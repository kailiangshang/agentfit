"""Orchestrator：训练循环控制器（九步闭环的持有者与任务分发者）。

确定性官员：路由表 + 状态机，无 LLM。对应实现文档 §三路由表、§八算法。
协同经总线留痕：每个 epoch 的关键步骤发消息（Auditor 落哈希链）。
"""
from __future__ import annotations

import copy
import re
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
from ..gates.human import GateType, ReviewDecision, ReviewRequest
from ..log.training_log import EpochEntry, TrainingLog
from ..models.config import TrainingConfig
from ..models.loss import Trace
from ..models.manifest import SampleSetPurpose
from ..models.evidence import CandidateManifest
from ..models.sample import Episode, EvaluationIdentity, TaskSample, canonical_hash
from ..models.solution import Solution


@dataclass
class StepOutcome:
    """一个 Step = 一个 adaptation Batch 的完整更新单元（正本 §Batch、Step、Epoch）。"""
    epoch: int
    step_index: int
    batch_size: int = 0
    passed: int = 0
    failed: int = 0
    execution_errors: int = 0
    proposals: int = 0
    applied: int = 0
    applied_changes: list = field(default_factory=list)
    rolled_back: bool = False
    cost_usd: float = 0.0
    loss_traces: list = field(default_factory=list)
    behavioral: dict = field(default_factory=dict)   # 本步行为正则值（供 λ 聚合）
    task_proposals: int = 0
    regularization_proposals: int = 0
    notes: list[str] = field(default_factory=list)


@dataclass
class EpochOutcome:
    epoch: int
    pass_rate: float                      # Epoch 级指标：validation 通过率（无 validation 样本时为 adaptation 聚合）
    adaptation_pass_rate: float = 0.0     # 本 Epoch 各 Batch 实际 Episode 聚合（不是重放）
    regression_verdict: str = "COMMIT"
    rolled_back: bool = False
    proposals_count: int = 0
    notes: list[str] = field(default_factory=list)
    converged: bool = False
    execution_errors: int = 0
    steps: int = 0
    validation: dict | None = None        # {total, passed, failed, errors, pass_rate, cost_usd}
    stop_reason: str | None = None


class Orchestrator:
    def __init__(self, solution: Solution, pool: SamplePool, executor: ExecutorBase,
                 config: TrainingConfig, bus: MessageBus | None = None,
                 run_dir: str | None = None, scenario: str = "default",
                 validation_samples: list | None = None):
        self.solution = solution
        self.pool = pool
        self.executor = executor
        self.config = config
        self.bus = bus or MessageBus()
        self.log = TrainingLog()
        self.regression_pool = RegressionPool()
        self.lambda_ctl = LambdaController(initial=dict(solution.lambda_values))
        self.outcomes: list[EpochOutcome] = []
        self.delivery_decision: ReviewDecision | None = None
        self.validation_samples = list(validation_samples or [])
        self._prev_solution = copy.deepcopy(solution)
        self._best = {"rate": -1.0, "solution": copy.deepcopy(solution), "version": solution.version}
        self._patience = 0
        self._stop_reason: str | None = None
        self.validation_series: list[float] = []
        self.runtime_provenance = executor.runtime_provenance()
        self.runtime_ref = canonical_hash(self.runtime_provenance)
        self._run_indices: dict[tuple[str, str], int] = {}
        self.auditor = None
        from ..agents.activity import ActivityTracker
        self.activity = ActivityTracker()
        if run_dir:
            from ..agents.auditor import Auditor
            from ..store.run_store import RunStore
            store = RunStore(run_dir)
            store.init_run({"run_kind": "training", "scenario": scenario,
                            "executor": type(executor).__name__,
                            "runtime_provenance": self.runtime_provenance,
                            "runtime_ref": self.runtime_ref,
                            "config": {"batch_size": config.batch_size, "max_epochs": config.max_epochs},
                            "solution_version_start": solution.version})
            store.save_task_samples(pool.all_tasks)
            store.save_solution_version(solution, note="初始最简方案（Simple First）")
            self.auditor = Auditor(store)

    # ---------- Step：一个 adaptation Batch 的完整更新单元 ----------
    def run_step(self, epoch: int, step_index: int, batch: list) -> StepOutcome:
        ctx = f"epoch{epoch}.step{step_index}"
        step = StepOutcome(epoch=epoch, step_index=step_index, batch_size=len(batch))

        # ① 前向执行
        traces = [
            self._send(
                MsgType.EXECUTE_BATCH,
                ctx,
                {"batch": batch},
                lambda _, s=s: self._execute_recorded(self.solution, s, epoch, "forward"),
            )
            for s in batch
        ]
        step.execution_errors = sum(trace.result == "ERROR" for trace in traces)
        step.cost_usd = sum(t.cost_usd for t in traces)
        if step.execution_errors:
            step.notes.append(f"{step.execution_errors} execution error(s) excluded from L1-L4 attribution")

        # ② 损失归因（Attributor 扇出；只对非 ERROR 失败归因）
        loss_traces = []
        for s, t in zip(batch, traces):
            if t.result != "ERROR" and not self.executor.evaluate(t, s.expected):
                loss_traces.append(self._send(MsgType.ATTRIBUTE, ctx, {"sample": s, "trace": t},
                                              lambda _, s=s, t=t: attribute_loss(s, t, self.solution)))
        step.loss_traces = loss_traces
        self.activity.record("attributor", "attribution", epoch, step_index,
            input_summary=f"{len(loss_traces)} 个失败样本归因",
            output_summary="; ".join(f"{lt.sample_id}→{lt.root_cause_layer}/{lt.failure_mode}"
                                     for lt in loss_traces[:3]) or "无失败")

        actionable_loss_traces = list(loss_traces)
        # 冻结分流：根因落在冻结元素的失败 → advisory（可追踪、非阻塞），不进提案聚合
        for trace in loss_traces:
            if self._root_element_frozen(trace):
                self._record_frozen_advisory(trace, epoch)
                actionable_loss_traces.remove(trace)
        low_confidence = [
            trace for trace in actionable_loss_traces
            if trace.confidence < self.config.attribution_confidence_floor
        ]
        if low_confidence:
            decision = self.config.review_policy.review(ReviewRequest(
                GateType.G1, "low-confidence attribution",
                {"sample_ids": [trace.sample_id for trace in low_confidence],
                 "confidence_floor": self.config.attribution_confidence_floor},
            ))
            if not decision.approved:
                blocked_ids = {trace.sample_id for trace in low_confidence}
                actionable_loss_traces = [
                    trace for trace in loss_traces if trace.sample_id not in blocked_ids
                ]
                step.notes.append("Human Gate blocked low-confidence attribution")

        # ③ 聚合
        agg = aggregate(actionable_loss_traces)
        self.activity.record("orchestrator", "aggregation", epoch, step_index,
            input_summary=f"{len(actionable_loss_traces)} 个失败样本",
            output_summary=f"瓶颈层={agg.bottleneck_layer or '无'} 模式数={len(agg.patterns)}")

        # ③' 正则计算（trained 子集；行为项用本步真实 traces）
        from ..core.regularization import compute_structural, compute_behavioral, \
            merge_behavioral, regularization_proposals
        step_reg = compute_structural(self.solution)
        step.behavioral = compute_behavioral(self.solution, traces, self._prev_solution)
        self.activity.record("validator", "validation", epoch, step_index,
            input_summary="结构正则 + 行为正则计算",
            output_summary=f"超阈: {step_reg.over_threshold or '无'}")

        # ④ 更新建议 = 任务梯度提案 ∪ 正则简化提案（λᵢ∇Rᵢ）+ 反向依赖传播
        proposals, notes = self._send(MsgType.PROPOSE, ctx,
                                      {"loss_traces": actionable_loss_traces},
                                      lambda _: propose_updates(aggregate(actionable_loss_traces), self.pool.by_id(), self.solution))
        from ..core.proposals import (propagate_reverse_dependencies,
                                      annotate_reg_conflicts, semantic_for_proposal)
        reg_proposals, reg_advisories = regularization_proposals(step_reg, self.solution)
        proposals = list(proposals) + reg_proposals + propagate_reverse_dependencies(proposals, self.solution)
        for advisory in reg_advisories:
            self._save_advisory(advisory)
        # 冲突标注 + 语义补全（提案带 semantic 落盘，重渲染一致）
        annotate_reg_conflicts(proposals, step_reg, self.solution)
        for proposal in proposals:
            if not proposal.semantic:
                proposal.semantic = semantic_for_proposal(proposal)
        step.notes.extend(notes)
        self.activity.record("architect", "proposal", epoch, step_index,
            input_summary=f"聚合损失 {len(agg.patterns)} 模式 + 正则违规",
            output_summary=f"任务提案 {sum(1 for p in proposals if p.origin=='task')} 正则提案 {sum(1 for p in proposals if p.origin=='regularization')}")
        step.task_proposals = sum(1 for p in proposals if p.origin == "task")
        step.regularization_proposals = sum(1 for p in proposals if p.origin == "regularization")
        step.proposals = len(proposals)

        # ⑥ 人审 G1（同一扇门，两类提案证据可辨：任务=样本证据 / 正则=指标证据）
        g1_decision = self.config.review_policy.review(ReviewRequest(
            GateType.G1, "solution updates",
            {"count": len(proposals),
             "proposals": [{
                 "origin": p.origin,
                 "layer": p.layer, "action": p.action,
                 "element": getattr(p.element, "id", str(p.element)),
                 "semantic": p.semantic,
                 "evidence": ({"type": "samples", "sample_ids": p.evidence_sample_ids}
                              if p.origin == "task" else p.reg_evidence),
                 "reg_conflict": p.reg_conflict,
             } for p in proposals]},
        ))
        approved = proposals if g1_decision.approved else []
        if proposals and not g1_decision.approved:
            step.notes.append("Human Gate blocked G1")

        step.passed = sum(1 for s, t in zip(batch, traces) if self.executor.evaluate(t, s.expected))
        step.failed = len(batch) - step.passed - step.execution_errors

        # ⑦ 原子应用（机械）+ ⑧ 回归验证（回归池 = adaptation 历史行为）
        self.activity.record("orchestrator", "cascade", epoch, step_index,
            input_summary=f"{len(proposals)} 条提案经 G1（{'批准' if approved else '拒绝'}）",
            output_summary=f"应用 {len(approved)} 条")
        if approved:
            previous_solution = copy.deepcopy(self.solution)
            tx = ChangeTransaction(self.solution, approved)
            try:
                candidate = tx.execute()
            except ValidationError as exc:
                step.rolled_back = True
                reason = "; ".join(exc.errors)
                step.notes.append("存在依赖验证失败：事务回滚")
                if "冻结" in reason:
                    self._save_advisory({
                        "kind": "frozen_boundary_rejected", "layer": "mixed",
                        "semantic": f"训练提出的变更触碰冻结边界被整体回滚（{reason}）；"
                                    f"建议用户复核冻结清单或自行调整预指定配置",
                        "rejected_changes": [
                            {"layer": p_.layer, "action": p_.action, "semantic": p_.semantic}
                            for p_ in approved],
                        "non_blocking": True,
                    })
                if self.auditor:
                    self.auditor.record_transaction(tx, rolled_back=True, reason=reason)
                candidate = None
            if candidate is not None:
                regression_traces = {
                    s.id: self._execute_recorded(candidate, s, epoch, "regression")
                    for s in self.regression_pool.samples
                }
                regression_errors = sorted(
                    sample_id
                    for sample_id, trace in regression_traces.items()
                    if trace.result == "ERROR"
                )
                reg_results = {
                    s.id: self.executor.evaluate(regression_traces[s.id], s.expected)
                    for s in self.regression_pool.samples
                    if s.id not in regression_errors
                }
                forgot = self.regression_pool.forget_check(reg_results)
                if regression_errors:
                    tx.rollback()
                    step.rolled_back = True
                    step.execution_errors += len(regression_errors)
                    step.notes.append(
                        "regression blocked by execution error: " + ", ".join(regression_errors)
                    )
                    if self.auditor:
                        self.auditor.record_transaction(
                            tx, rolled_back=True,
                            reason=f"regression execution error: {regression_errors}",
                        )
                elif forgot:
                    tx.rollback()
                    step.rolled_back = True
                    step.notes.append(f"回归遗忘 {len(forgot)} 个样本：回滚")
                    if self.auditor:
                        self.auditor.record_transaction(tx, rolled_back=True, reason=f"回归遗忘 {forgot}")
                else:
                    self._prev_solution = previous_solution
                    self.solution = candidate
                    step.applied = len(approved)
                    self.activity.record("validator", "regression", epoch, step_index,
                        input_summary=f"回归池 {len(self.regression_pool.samples)} 样本重放",
                        output_summary="COMMIT（零遗忘）")
                    step.applied_changes = [
                        {"layer": p.layer, "action": p.action,
                         "element": getattr(p.element, "id", str(p.element))}
                        for p in approved
                    ]
                    if self.auditor:
                        self.auditor.record_transaction(tx, rolled_back=False)
                        self.auditor.store.save_solution_version(
                            candidate, note=f"epoch {epoch} step {step_index} 更新")

        # 回归池只由 adaptation Episode 更新
        for s, t in zip(batch, traces):
            if t.result != "ERROR":
                self.regression_pool.add(s, self.executor.evaluate(t, s.expected))

        if self.auditor:
            self.auditor.store.save_step(epoch, step_index, {
                "epoch": epoch, "step_index": step_index, "batch_size": step.batch_size,
                "passed": step.passed, "failed": step.failed,
                "execution_errors": step.execution_errors,
                "proposals": step.proposals, "applied": step.applied,
                "task_proposals": step.task_proposals,
                "regularization_proposals": step.regularization_proposals,
                "rolled_back": step.rolled_back, "cost_usd": round(step.cost_usd, 6),
                "loss_attribution": {k: int(v * agg.total) for k, v in agg.layer_share.items()},
                "notes": step.notes,
            })
        return step

    # ---------- Validation：Epoch 末、只读、不产生 ChangeProposal ----------
    def run_validation(self, epoch: int) -> dict:
        total = passed = errors = 0
        cost = 0.0
        for sample in self.validation_samples:
            trace = self._execute_recorded(self.solution, sample, epoch, "validation")
            total += 1
            cost += trace.cost_usd
            if trace.result == "ERROR":
                errors += 1
            elif self.executor.evaluate(trace, sample.expected):
                passed += 1
        record = {
            "epoch": epoch, "total": total, "passed": passed,
            "failed": total - passed - errors, "errors": errors,
            "pass_rate": (passed / total) if total else None,
            "cost_usd": round(cost, 6),
            "candidate_version": self.solution.version,
        }
        self.activity.record("validator", "regression", epoch, 0,
            input_summary=f"validation 集 {total} 样本只读评价",
            output_summary=f"{passed}/{total} 通过")
        if self.auditor:
            self.auditor.store.save_validation(epoch, record)
        return record

    # ---------- Epoch：完整覆盖 adaptation + 冻结 + validation + Early Stopping ----------
    def run_epoch(self, epoch: int) -> EpochOutcome:
        batches = self.pool.epoch_batches(self.config.batch_size, epoch)
        outcome = EpochOutcome(epoch=epoch, pass_rate=0.0, steps=len(batches))

        steps: list[StepOutcome] = []
        for index, batch in enumerate(batches, start=1):
            steps.append(self.run_step(epoch, index, batch))
        all_loss_traces = [lt for s in steps for lt in s.loss_traces]
        applied_changes = [c for s in steps for c in s.applied_changes]
        outcome.execution_errors = sum(s.execution_errors for s in steps)
        outcome.proposals_count = sum(s.proposals for s in steps)
        outcome.rolled_back = any(s.rolled_back for s in steps)
        outcome.notes = [n for s in steps for n in s.notes]

        executed = sum(s.passed + s.failed for s in steps)
        outcome.adaptation_pass_rate = (sum(s.passed for s in steps) / executed) if executed else 0.0

        # λ 调节（Epoch 级）：结构正则 + 各 Step 行为正则聚合（真实 traces 派生）
        merged_behavioral: dict[str, float] = {}
        for s_step in steps:
            for key, value in s_step.behavioral.items():
                merged_behavioral[key] = max(merged_behavioral.get(key, 0.0), value)
        reg = merge_behavioral(compute_structural(self.solution), merged_behavioral)
        new_lambdas, lambda_events = self.lambda_ctl.observe(reg)
        for event in lambda_events:
            if event.get("gate") != GateType.G2.value:
                continue
            decision = self.config.review_policy.review(
                ReviewRequest(GateType.G2, "lambda adjustment", event)
            )
            if decision.approved:
                new_lambdas.update(event["proposed"])
                self.lambda_ctl.initial = dict(new_lambdas)
            else:
                outcome.notes.append("Human Gate blocked G2 lambda adjustment")
        self.solution.lambda_values = new_lambdas

        # Epoch 末冻结 Candidate，运行 validation（只读；不进归因/建议/回归池）
        validation = self.run_validation(epoch) if self.validation_samples else None
        outcome.validation = validation
        if validation and validation["pass_rate"] is not None:
            outcome.pass_rate = validation["pass_rate"]
            self.validation_series.append(validation["pass_rate"])
        else:
            outcome.pass_rate = outcome.adaptation_pass_rate

        cost_usd = sum(s.cost_usd for s in steps) + (validation["cost_usd"] if validation else 0.0)

        # ⑨ 日志（Auditor 哈希链）
        loss_distribution: dict[str, int] = {}
        for lt in all_loss_traces:
            loss_distribution[lt.root_cause_layer] = loss_distribution.get(lt.root_cause_layer, 0) + 1
        self.log.append(EpochEntry(
            epoch=epoch, solution_version=self.solution.version, pass_rate=outcome.pass_rate,
            loss_distribution=loss_distribution,
            updates_applied=applied_changes,
            regularization={k: round(v, 4) for k, v in reg.layer_reg.items()},
            behavioral={},
            regression={"tested": len(self.regression_pool.samples),
                        "passed": sum(1 for s in self.regression_pool.samples
                                      if s.id in self.regression_pool.passed_ids)},
            lambda_values=dict(self.solution.lambda_values),
            cost_usd=cost_usd,
            execution_errors=outcome.execution_errors,
            rolled_back=outcome.rolled_back,
            note="; ".join(outcome.notes),
        ))
        if self.auditor:
            new_traffic = self.bus.traffic[self._traffic_cursor:]
            self._traffic_cursor = len(self.bus.traffic)
            self.auditor.persist_epoch(epoch, self.log.entries[-1], all_loss_traces, new_traffic)
        self.activity.save(self.auditor.store.root if self.auditor else "/tmp/agentfit-no-store", epoch)

        # Early Stopping（确定性 Validator 裁决，停止原因可重算）
        outcome.stop_reason = self._decide_stop(epoch)
        outcome.converged = outcome.stop_reason == "no_improvement"
        self.outcomes.append(outcome)
        return outcome

    # ---------- 收敛 / 预算 / Early Stopping ----------
    def _decide_stop(self, epoch: int) -> str | None:
        """确定性 Validator 裁决：候选晋升/继续/恢复/停止。返回规范停止原因或 None（继续）。

        停止原因全部可从 RunStore 重算：validation 曲线 + 预算 + 轮数上限。
        """
        if self.budget_exceeded():
            return "budget_exceeded"
        if not self.validation_samples:
            return None
        rate = self.validation_series[-1]
        best = self._best["rate"]
        if rate > best + self.config.validation_min_improvement:
            self._best = {"rate": rate, "solution": copy.deepcopy(self.solution),
                          "version": self.solution.version}
            self._patience = 0
            return None
        if best >= 0 and rate < best - self.config.validation_degradation:
            # validation 退化 → 恢复已保留最佳候选并停止
            self.solution = copy.deepcopy(self._best["solution"])
            self._prev_solution = copy.deepcopy(self.solution)
            return "validation_degraded"
        self._patience += 1
        if self._patience >= self.config.validation_patience:
            return "no_improvement"
        return None

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

    # ---------- 冻结分流与 advisory ----------
    def _root_element_frozen(self, loss_trace) -> bool:
        element_id = loss_trace.root_cause_element
        if not element_id or element_id == "-":
            return False
        for lookup in (self.solution.knowledge(element_id),
                       self.solution.tool(element_id),
                       self.solution.atom(element_id)):
            if lookup is not None:
                return bool(getattr(lookup, "frozen", False))
        return False

    def _record_frozen_advisory(self, loss_trace, epoch: int) -> None:
        self._save_advisory({
            "kind": "frozen_root_cause", "layer": loss_trace.root_cause_layer,
            "metric": None,
            "semantic": f"样本 {loss_trace.sample_id} 失败的根因在用户预指定的元素 "
                        f"“{loss_trace.root_cause_element}”（{loss_trace.detail}）；"
                        f"训练不修改冻结元素，建议用户复核该配置",
            "frozen_elements": [loss_trace.root_cause_element],
            "sample_id": loss_trace.sample_id, "epoch": epoch,
            "non_blocking": True,
        })

    def _save_advisory(self, record: dict) -> None:
        if self.auditor:
            self.auditor.store.save_optimization_suggestion(record)

    # ---------- 总线 ----------
    def _execute_recorded(
        self, solution: Solution, sample: TaskSample, epoch: int, phase: str,
    ):
        trace, identity = self.execute_evaluation(solution, sample)
        if not self.auditor:
            return trace

        trace_path = self.auditor.store.save_training_trace(epoch, phase, identity, trace)
        episode = Episode(
            identity=identity,
            trace_ref=trace_path.relative_to(self.auditor.store.root).as_posix(),
            result=trace.result,
            cost_usd=trace.cost_usd,
            evidence_hash=canonical_hash(trace),
            risk_events=len(trace.risk_events),
            runtime_ref=trace.runtime_ref,
        )
        self.auditor.store.save_training_episode(epoch, phase, episode)
        return trace

    def execute_evaluation(
        self, solution: Solution, sample: TaskSample,
    ) -> tuple[Trace, EvaluationIdentity]:
        """Execute once and allocate the run-wide evaluation identity."""
        trace = self.executor.execute(solution, sample)
        if not trace.runtime_ref:
            trace.runtime_ref = self.runtime_ref
        manifest = CandidateManifest.for_solution(solution)
        if self.auditor:
            self.auditor.store.save_training_candidate_manifest(manifest)
        counter_key = (manifest.candidate_ref, sample.content_hash)
        run_index = self._run_indices.get(counter_key, 0)
        self._run_indices[counter_key] = run_index + 1
        identity = EvaluationIdentity(manifest.candidate_ref, sample.ref, run_index)
        return trace, identity

    def _send(self, msg_type: MsgType, ctx: str, payload: dict, fn) -> object:
        """发消息经总线（角色处理 + Auditor 留痕）；无注册角色时回退本地确定性内核。"""
        msg = TaskMsg(to="*", type=msg_type, payload=payload, context_ref=ctx)
        results = self.bus.dispatch(msg)
        if results:
            return results[0].output
        return fn(msg)

    def finalize_delivery(self, evidence: dict | None = None) -> ReviewDecision:
        """Run G3 only after the caller has persisted final evaluation evidence."""
        purposes = {purpose.value for purpose in SampleSetPurpose}
        evaluations = evidence.get("evaluation_by_purpose") if isinstance(evidence, dict) else None
        candidate_ref = evidence.get("candidate_ref") if isinstance(evidence, dict) else None
        objective_ref = evidence.get("objective_ref") if isinstance(evidence, dict) else None
        acceptance_ref = evidence.get("acceptance_ref") if isinstance(evidence, dict) else None
        acceptance_met = evidence.get("acceptance_met") if isinstance(evidence, dict) else None
        complete = (
            evidence is not None
            and evidence.get("candidate_frozen") is True
            and isinstance(candidate_ref, str)
            and re.fullmatch(r"[0-9a-f]{64}", candidate_ref) is not None
            and isinstance(evaluations, dict)
            and set(evaluations) == purposes
            and isinstance(objective_ref, str)
            and re.fullmatch(r"[0-9a-f]{64}", objective_ref) is not None
            and isinstance(acceptance_ref, str)
            and re.fullmatch(r"[0-9a-f]{64}", acceptance_ref) is not None
            and isinstance(acceptance_met, bool)
            and isinstance(evidence.get("acceptance_failures"), list)
        )
        if complete:
            for metrics in evaluations.values():
                if not isinstance(metrics, dict):
                    complete = False
                    break
                total = metrics.get("total")
                outcomes = sum(metrics.get(key, 0) for key in ("passed", "failed", "errors"))
                if not isinstance(total, int) or total <= 0 or outcomes != total:
                    complete = False
                    break
        if not complete:
            raise ValueError("complete final evaluation evidence is required before G3")
        summary = dict(getattr(self, "_last_summary", {}))
        summary.update(evidence or {})
        if not acceptance_met:
            failures = summary.get("acceptance_failures") or ["objective not met"]
            self.delivery_decision = ReviewDecision(
                False,
                "objective acceptance failed: " + "; ".join(failures),
                "objective-gate",
            )
        else:
            self.delivery_decision = self.config.review_policy.review(
                ReviewRequest(GateType.G3, "delivery boundary", summary)
            )
        summary["delivery_approved"] = self.delivery_decision.approved
        summary["delivery_review_reason"] = self.delivery_decision.reason
        summary["delivery_reviewer"] = self.delivery_decision.reviewer
        summary["delivery_conditions"] = list(self.delivery_decision.conditions)
        if self.auditor:
            from ..delivery.approval import create_delivery_decision
            decision_artifact = create_delivery_decision(
                self.auditor.store, self.delivery_decision, summary,
            )
            self.auditor.store.save_delivery_decision(decision_artifact)
            summary["delivery_decision_hash"] = decision_artifact["decision_hash"]
            self.auditor.persist_summary(summary)
        self._last_summary = summary
        return self.delivery_decision

    def run_train_replay(self) -> dict:
        """显式诊断重放：完整 adaptation 一次，分型 train_replay，不冒充 validation。

        成本单独核算（summary.train_replay），不进入 epoch 成本或总成本曲线。
        """
        total = passed = errors = 0
        cost = 0.0
        epoch = len(self.outcomes) + 1
        for sample in self.pool.all_tasks:
            trace = self._execute_recorded(self.solution, sample, epoch, "train_replay")
            total += 1
            cost += trace.cost_usd
            if trace.result == "ERROR":
                errors += 1
            elif self.executor.evaluate(trace, sample.expected):
                passed += 1
        record = {"total": total, "passed": passed, "failed": total - passed - errors,
                  "errors": errors, "pass_rate": (passed / total) if total else None,
                  "cost_usd": round(cost, 6), "candidate_version": self.solution.version}
        if self.auditor:
            self.auditor.store.save_train_replay(record)
            summary = self.auditor.store.load_json("summary.json") \
                if (self.auditor.store.root / "summary.json").exists() else {}
            summary["train_replay"] = record
            self.auditor.persist_summary(summary)
        return record

    def train(self) -> list[EpochOutcome]:
        self._traffic_cursor = 0
        stop_reason = "max_epochs"
        for epoch in range(1, self.config.max_epochs + 1):
            outcome = self.run_epoch(epoch)
            if outcome.stop_reason:
                stop_reason = outcome.stop_reason
                break
        self._stop_reason = stop_reason
        series = self.log.pass_rate_series()
        summary = {
            "epochs_run": len(self.outcomes),
            "final_pass_rate": series[-1] if series else None,
            "final_solution_version": self.solution.version,
            "lambda_values": dict(self.solution.lambda_values),
            "total_cost_usd": round(self.total_cost(), 4),
            "converged": stop_reason in ("no_improvement", "validation_degraded"),
            "budget_exceeded": self.budget_exceeded(),
            "log_chain_valid": self.log.verify(),
            "stop_reason": stop_reason,
            "validation_series": list(self.validation_series),
            "best_validation_rate": self._best["rate"] if self._best["rate"] >= 0 else None,
            "best_candidate_version": self._best["version"],
        }
        self._last_summary = summary
        summary["delivery_approved"] = False
        summary["delivery_review_reason"] = "G3 deferred until final evaluation evidence is persisted"
        summary["delivery_reviewer"] = "unassigned"
        if self.auditor:
            self.auditor.persist_summary(summary)
            # 运行完成仪制：训练结果 + 对 AgentFit 自身的建议
            from ..log.meta_review import generate_meta_review
            from ..log.report import generate_report
            generate_report(self.auditor.store.root)
            generate_meta_review(self.auditor.store.root)
            # 非阻塞叙事：LLM 失败不影响 dashboard
            try:
                from ..dashboard.narrative import generate_narrative
                generate_narrative(self.auditor.store.root)
            except Exception:
                pass
        return self.outcomes
