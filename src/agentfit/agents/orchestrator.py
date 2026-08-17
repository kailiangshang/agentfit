"""Orchestrator：训练循环控制器（九步闭环的持有者与任务分发者）。

确定性官员：路由表 + 状态机，无 LLM。对应实现文档 §三路由表、§八算法。
协同经总线留痕：每个 epoch 的关键步骤发消息（Auditor 落哈希链）。
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from ..bus.messages import MessageBus, MsgType, ResultMsg, TaskMsg
from ..core.aggregation import aggregate
from ..core.attribution import attribute_loss
from ..core.proposals import propose_updates
from ..core.regularization import (LambdaController, RegReport, compute_behavioral,
                                   compute_structural, merge_behavioral)
from ..core.regression import RegressionPool, validate_regression
from ..core.transaction import ChangeTransaction, ValidationError
from ..data.sample_pool import SamplePool
from ..executors.base import ExecutorBase
from ..log.training_log import EpochEntry, TrainingLog
from ..models.config import TrainingConfig
from ..models.solution import Solution


@dataclass
class EpochOutcome:
    epoch: int
    pass_rate: float
    regression_verdict: str = "COMMIT"
    rolled_back: bool = False
    proposals_count: int = 0
    notes: list[str] = field(default_factory=list)
    converged: bool = False


class Orchestrator:
    def __init__(self, solution: Solution, pool: SamplePool, executor: ExecutorBase,
                 config: TrainingConfig, bus: MessageBus | None = None,
                 run_dir: str | None = None, scenario: str = "default"):
        self.solution = solution
        self.pool = pool
        self.executor = executor
        self.config = config
        self.bus = bus or MessageBus()
        self.log = TrainingLog()
        self.regression_pool = RegressionPool()
        self.lambda_ctl = LambdaController(initial=dict(solution.lambda_values))
        self.outcomes: list[EpochOutcome] = []
        self._prev_solution = copy.deepcopy(solution)
        self.auditor = None
        if run_dir:
            from ..agents.auditor import Auditor
            from ..store.run_store import RunStore
            store = RunStore(run_dir)
            store.init_run({"scenario": scenario, "executor": type(executor).__name__,
                            "config": {"batch_size": config.batch_size, "max_epochs": config.max_epochs},
                            "solution_version_start": solution.version})
            store.save_samples(pool.all_samples)
            store.save_solution_version(solution, note="初始最简方案（Simple First）")
            self.auditor = Auditor(store)

    # ---------- 单轮九步 ----------
    def run_epoch(self, epoch: int) -> EpochOutcome:
        ctx = f"epoch{epoch}"
        outcome = EpochOutcome(epoch, 0.0)

        # ① 前向执行
        batch = self.pool.next_batch(self.config.batch_size)
        traces = [self._send(MsgType.EXECUTE_BATCH, ctx, {"batch": batch}, lambda _: self.executor.execute(self.solution, s)) for s in batch]

        # ② 损失归因（Attributor 扇出）
        loss_traces = []
        for s, t in zip(batch, traces):
            if not self.executor.evaluate(t, s.expected):
                loss_traces.append(self._send(MsgType.ATTRIBUTE, ctx, {"sample": s, "trace": t},
                                              lambda _, s=s, t=t: attribute_loss(s, t, self.solution)))

        # ③ 聚合 + 正则（Validator/Auditor 计算）
        prev = self._prev_solution
        reg = merge_behavioral(compute_structural(self.solution),
                               compute_behavioral(self.solution, traces, prev))
        agg = aggregate(loss_traces)

        # ④ 更新建议（Architect）
        proposals, notes = self._send(MsgType.PROPOSE, ctx,
                                      {"loss_traces": loss_traces},
                                      lambda _: propose_updates(aggregate(loss_traces), self.pool.by_id(), self.solution))
        outcome.notes = notes
        outcome.proposals_count = len(proposals)

        # ⑤ λ 调节
        new_lambdas, _level2 = self.lambda_ctl.observe(reg)
        self.solution.lambda_values = new_lambdas

        # ⑥ 人审 G1（硬同步点；不批准 = 本轮空转）
        approved = proposals if self.config.review_policy.review_updates(proposals) else []

        passed = sum(1 for s, t in zip(batch, traces) if self.executor.evaluate(t, s.expected))
        outcome.pass_rate = passed / len(batch)

        # ⑦ 原子应用（机械）+ ⑧ 回归验证
        if approved:
            previous_solution = copy.deepcopy(self.solution)
            tx = ChangeTransaction(self.solution, approved)
            try:
                candidate = tx.execute()
            except ValidationError:
                outcome.rolled_back = True
                outcome.notes.append("存在依赖验证失败：事务回滚")
                if self.auditor:
                    self.auditor.record_transaction(tx, rolled_back=True, reason="依赖验证失败")
                candidate = None
            if candidate is not None:
                reg_results = {s.id: self.executor.evaluate(self.executor.execute(candidate, s), s.expected)
                               for s in self.regression_pool.samples}
                forgot = self.regression_pool.forget_check(reg_results)
                if forgot:
                    tx.rollback()
                    outcome.rolled_back = True
                    outcome.notes.append(f"回归遗忘 {len(forgot)} 个样本：回滚")
                    if self.auditor:
                        self.auditor.record_transaction(tx, rolled_back=True, reason=f"回归遗忘 {forgot}")
                else:
                    self._prev_solution = previous_solution
                    self.solution = candidate
                    if self.auditor:
                        self.auditor.record_transaction(tx, rolled_back=False)
                        self.auditor.store.save_solution_version(candidate, note=f"epoch {epoch} 更新")
                    passed_c = sum(1 for s in self.pool.group("train")
                                   if self.executor.evaluate(self.executor.execute(candidate, s), s.expected))
                    outcome.pass_rate = passed_c / max(1, len(self.pool.group("train")))

        # ⑨ 日志（Auditor 哈希链）
        self.log.append(EpochEntry(
            epoch=epoch, solution_version=self.solution.version, pass_rate=outcome.pass_rate,
            loss_distribution=agg.layer_share_counts() if hasattr(agg, "layer_share_counts") else
            {k: int(v * agg.total) for k, v in agg.layer_share.items()},
            updates_applied=[{"layer": p.layer, "action": p.action, "element": getattr(p.element, "id", str(p.element))}
                             for p in (approved if not outcome.rolled_back else [])],
            regularization={k: round(v, 4) for k, v in reg.layer_reg.items()},
            behavioral={k: round(v, 4) for k, v in reg.values.items() if k in ("chain_coverage", "human_intervention", "communication_overhead", "atom_growth")},
            regression={"tested": len(self.regression_pool.samples),
                        "passed": sum(1 for s in self.regression_pool.samples
                                      if self.executor.evaluate(self.executor.execute(self.solution, s), s.expected))},
            lambda_values=dict(self.solution.lambda_values),
            cost_usd=sum(t.cost_usd for t in traces),
            rolled_back=outcome.rolled_back,
            note="; ".join(outcome.notes),
        ))
        self.regression_pool.update({s.id: self.executor.evaluate(t, s.expected)
                                     for s, t in zip(batch, traces)})
        for s, t in zip(batch, traces):
            self.regression_pool.add(s, self.executor.evaluate(t, s.expected))

        # ⑨ 落链 + 落盘（Auditor）——保存完整链记录（entry+hash+previous_hash）
        if self.auditor:
            new_traffic = self.bus.traffic[self._traffic_cursor:]
            self._traffic_cursor = len(self.bus.traffic)
            self.auditor.persist_epoch(epoch, self.log.entries[-1], loss_traces, new_traffic)

        outcome.converged = self._check_convergence()
        self.outcomes.append(outcome)
        return outcome

    # ---------- 收敛 / 预算 ----------
    def _check_convergence(self) -> bool:
        series = self.log.pass_rate_series()
        if len(series) < self.config.convergence_window:
            return False
        window = series[-self.config.convergence_window:]
        return max(window) - min(window) < self.config.min_improvement

    def total_cost(self) -> float:
        return sum(e["entry"]["cost_usd"] for e in self.log.entries)

    def budget_exceeded(self) -> bool:
        return self.total_cost() > self.config.budget_usd

    # ---------- 总线 ----------
    def _send(self, msg_type: MsgType, ctx: str, payload: dict, fn) -> object:
        """发消息经总线（角色处理 + Auditor 留痕）；无注册角色时回退本地确定性内核。"""
        msg = TaskMsg(to="*", type=msg_type, payload=payload, context_ref=ctx)
        results = self.bus.dispatch(msg)
        if results:
            return results[0].output
        return fn(msg)

    def train(self) -> list[EpochOutcome]:
        self._traffic_cursor = 0
        for epoch in range(1, self.config.max_epochs + 1):
            outcome = self.run_epoch(epoch)
            if outcome.converged or self.budget_exceeded():
                break
        if self.auditor:
            series = self.log.pass_rate_series()
            self.auditor.persist_summary({
                "epochs_run": len(self.outcomes),
                "final_pass_rate": series[-1] if series else None,
                "final_solution_version": self.solution.version,
                "lambda_values": dict(self.solution.lambda_values),
                "total_cost_usd": round(self.total_cost(), 4),
                "converged": bool(self.outcomes and self.outcomes[-1].converged),
                "budget_exceeded": self.budget_exceeded(),
                "log_chain_valid": self.log.verify(),
            })
            # 运行完成仪制：训练结果 + 对 AgentFit 自身的建议
            from ..log.meta_review import generate_meta_review
            from ..log.report import generate_report
            generate_report(self.auditor.store.root)
            generate_meta_review(self.auditor.store.root)
        return self.outcomes
