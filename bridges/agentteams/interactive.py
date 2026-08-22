#!/usr/bin/env python3
"""AgentFit 交互式入口：用户 ↔ Steward 对话 → G0 冻结 → 训练（G1 实时审批）。

用法：
  PYTHONPATH=src .venv/bin/python -m agentfit.interactive --bundle <bundle.json> --output <run_dir>

流程：
  1. Steward 呈现材料理解（语义双轨）→ 用户确认
  2. 样本充分性判定 → 用户确认
  3. 初始方案概览 → G0 冻结确认
  4. 训练循环：每轮 G1 提案以语义摘要呈现 → 用户 y/n
  5. 结束后：训练结果 + AgentFit 建议 + dashboard 路径
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _input(prompt: str) -> str:
    """带默认值的用户输入。"""
    try:
        return input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n（中断）")
        sys.exit(1)


def _confirm(prompt: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    answer = _input(f"{prompt} {hint} ")
    if not answer:
        return default
    return answer in ("y", "yes", "是")


def _show(text: str) -> None:
    print(f"\n{'='*60}")
    print(text)
    print(f"{'='*60}")


def run_interactive(bundle_path: Path, output_dir: Path, model: str = "deepseek-v4-flash") -> None:
    """交互式训练入口。"""
    import os
    sys.path.insert(0, str(REPO / "src"))
    sys.path.insert(0, str(REPO))

    from plugins.materials.compiler import compile_material_bundle
    from agentfit.models.taxonomy import registry_from_dict

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    compiled = compile_material_bundle(bundle)
    registry = registry_from_dict(bundle.get("taxonomy") or {})

    # ============ 1. Steward：材料理解 ============
    _show("📋 Steward · 材料理解")
    atoms = compiled.capability_inventory.atoms
    tools = compiled.capability_inventory.tools
    frozen_atoms = sum(1 for a in atoms if a.frozen)
    samples = compiled.task_samples
    purposes = {}
    for s in samples:
        p = s.constraints.get("purpose", "unknown") if hasattr(s, "constraints") else "unknown"
        purposes[p] = purposes.get(p, 0) + 1

    # 从 sample_sets 获取分布
    set_counts = {}
    for manifest in compiled.sample_sets.manifests:
        set_counts[manifest.purpose.value] = len(manifest.sample_refs)

    print(f"""
  场景：{bundle.get('scenario', '?')}
  
  你提供了：
  · {len(atoms)} 个原子接口（其中 {frozen_atoms} 个🔒基础设施，训练不可修改）
  · {len(tools)} 个安全封装能力（训练可优化）
  
  样本分布：
  · 训练用（adaptation）：{set_counts.get('adaptation', '?')} 个
  · 验证用（validation）：{set_counts.get('validation', '?')} 个
  · 封存测试（sealed_holdout）：{set_counts.get('sealed_holdout', '?')} 个
  · 压力测试（stress_and_failure）：{set_counts.get('stress_and_failure', '?')} 个
  
  评价方式：执行动作与预期动作匹配 = 通过
""")

    if not _confirm("以上理解正确吗？"):
        print("请修正 bundle 后重新运行。")
        return

    # ============ 2. 样本充分性 ============
    _show("📊 Steward · 样本充分性")
    adaptation_count = set_counts.get("adaptation", 0)
    if adaptation_count < 5:
        print(f"  ⚠️ 训练样本只有 {adaptation_count} 个，建议 ≥5 个。")
        if not _confirm("仍要继续吗？", default=False):
            return
    else:
        print(f"  ✓ {adaptation_count} 个训练样本，初始训练足够。")

    # ============ 3. 初始方案 + G0 ============
    _show("🏗️ Steward · 初始方案（Simple First）")
    from agentfit.solution.builder import build_candidate
    solution = build_candidate(list(samples), compiled.sample_sets, compiled.capability_inventory)
    rules = solution.routing_rules()
    agents = solution.L4_topology.agents

    print(f"""
  初始方案从最简起步：
  · L1 原子：{len(solution.L1_atoms)} 个（全部来自你的清单）
  · L2 能力：{len(solution.L2_tools)} 个（全部来自你的清单）
  · L3 知识：{len(rules)} 条路由规则（从训练样本归纳）
  · L4 拓扑：{len(agents)} 个 Agent（{'单 Agent' if len(agents) == 1 else '多 Agent'}）
  
  路由规则：
""")
    for r in rules[:5]:
        desc = r.description or ""
        print(f"    · {r.condition or '(兜底)'} → {r.dispatches_to or '?'}  {desc[:40]}")
    if len(rules) > 5:
        print(f"    ... 共 {len(rules)} 条")

    if not _confirm(f"""
  确认冻结以下内容？（G0）
  · 样本集（{sum(set_counts.values())} 个样本的集合划分）
  · 评价目标（通过率阈值等）
  · 类型学注册（{len(registry.customs)} 个自定义类型）
  · 冻结清单（L1 原子 {frozen_atoms} 个🔒）
"""):
        print("G0 未确认，训练不开始。")
        return

    print("  ✓ G0 冻结完成。")

    # ============ 3.5 用户代理人（Delegate Reviewer）============
    _show("🤖 Steward · 用户代理审批")
    delegate_preferences = None
    if _confirm("""
  是否允许 Agent 模拟你进行后续审批（G1 方案变更等）？
  
  允许后你只需写一次偏好习惯，Agent 会按照你的标准自动审批，
  所有决策会落盘可追溯。不允许则每轮都需要你在终端手动确认。
"""):
        print("""
  请写下你的审批偏好习惯（自由文本，写完按回车）：
  例：我偏好保守变更，单层修改优先批准；拓扑变更必须暂停问我；
      涉及人工门禁的调整要说明理由；通过率低于60%时倾向激进修改。
""")
        delegate_preferences = input("  你的偏好：").strip()
        if delegate_preferences:
            print(f"""
  ✓ 已记录你的审批偏好。
  后续 G1 提案将由 Agent 按以下标准审阅：
  ┌─────────────────────────────────────────┐
  │ {delegate_preferences[:60]}{'...' if len(delegate_preferences) > 60 else ''} │
  └─────────────────────────────────────────┘
  所有审批决策会标注"delegate:用户代理人"并落盘。
""")
        else:
            print("  （未写偏好，回退到终端手动审批）")
            delegate_preferences = None

    # ============ 4. 训练循环 ============
    from agentfit.agents.orchestrator import Orchestrator
    from agentfit.agents.team import build_team
    from agentfit.data.sample_pool import SamplePool
    # 真实执行：AgentTeams Worker → Matrix → deepseek-v4-flash
    from bridges.agentteams.candidate_sandbox import (CandidateWorkerLifecycle,
        DockerAgentTeamsControl, render_candidate_worker)
    from bridges.agentteams.matrix_sandbox import (MatrixHttpTransport,
        MatrixSandboxAdapter, load_manager_matrix_credentials)
    from bridges.agentteams.executor import AgentTeamsSandboxExecutor
    from agentfit.models.evidence import CandidateManifest
    from agentfit.models.config import TrainingConfig, AutoApprove
    from agentfit.models.manifest import SampleSetPurpose

    # 分离 adaptation / validation
    adaptation_manifest = compiled.sample_sets.by_purpose(SampleSetPurpose.ADAPTATION)
    adaptation_ids = {ref.sample_id for ref in adaptation_manifest.sample_refs}
    adaptation_samples = [s for s in samples if s.id in adaptation_ids]
    validation_samples = [s for s in samples if s.id not in adaptation_ids]

    training_cfg = bundle.get("training", {})
    if delegate_preferences:
        gate_policy = DelegatedGatePolicy(preferences=delegate_preferences)
        print(f"  🤖 审批模式：用户代理人（偏好已注入）")
    else:
        gate_policy = InteractiveGatePolicy()
        print(f"  👤 审批模式：终端手动")

    config = TrainingConfig(
        batch_size=int(training_cfg.get("batch_size", len(adaptation_samples))),
        max_epochs=int(training_cfg.get("max_epochs", 3)),
        review_policy=gate_policy,
    )

    # 真实执行链路：起一个专用 Worker
    candidate = CandidateManifest.for_solution(solution)
    _show("🔌 启动 AgentTeams 真实执行 Worker")
    lc = CandidateWorkerLifecycle(DockerAgentTeamsControl("agentteams-manager"))
    worker_manifest = render_candidate_worker(
        candidate_ref=candidate.candidate_ref,
        run_id=f"interactive-{output_dir.name}",
        model_ref=model,
    )
    endpoint = lc.provision(worker_manifest, timeout_seconds=300)
    print(f"  Worker 就绪: {endpoint.name}（deepseek-v4-flash）")
    credentials = load_manager_matrix_credentials(homeserver_override="http://127.0.0.1:18080")
    transport = MatrixHttpTransport(credentials)
    sandbox = MatrixSandboxAdapter(transport, room_id=endpoint.room_id,
                                    worker_user_id=endpoint.matrix_user_id)
    raw_executor = AgentTeamsSandboxExecutor(
        sandbox,
        deployment_ref=f"agentteams://worker/{endpoint.name}",
        sandbox_ref=f"agentteams://worker/{endpoint.name}",
        model_ref=model,
        binding_mode="semantic_dry_run",
        cost_accounting="unavailable",
    )
    executor = ProgressExecutor(raw_executor, total_samples=len(adaptation_samples),
                                 label="adaptation")

    try:
        orchestrator = Orchestrator(
            solution, SamplePool(adaptation_samples), executor, config,
            run_dir=str(output_dir), scenario=bundle.get("scenario", "interactive"),
            validation_samples=validation_samples,
        )
        build_team(orchestrator)

        _show("🔄 训练开始")
        for outcome in orchestrator.train():
            _show(f"Epoch {outcome.epoch} 完成")
            print(f"  adaptation 通过率：{outcome.adaptation_pass_rate:.0%}")
            if outcome.validation:
                print(f"  validation 通过率：{outcome.validation['pass_rate']:.0%}")
            print(f"  停止原因：{outcome.stop_reason or '继续'}")
            if outcome.notes:
                print(f"  备注：{', '.join(outcome.notes[:3])}")

        # ============ 5. 结果 ============
        _show("✅ 训练完成")
        print(f"""
  最终方案版本：v{orchestrator.solution.version}
  Dashboard：{output_dir}/dashboard.html
  训练报告：{output_dir}/training_report.md
  AgentFit 建议：{output_dir}/meta_review.md

  在浏览器打开：http://localhost:8765/{output_dir.name}/dashboard.html
""")
    finally:
        lc.retire(endpoint.name, timeout_seconds=120)
        print("  Worker 已回收")


from agentfit.models.config import AutoApprove


class ProgressExecutor:
    """包装任意 ExecutorBase，逐样本推送进度到终端。"""

    def __init__(self, inner_executor, total_samples: int, label: str = "执行"):
        self.inner = inner_executor
        self.total = total_samples
        self.count = 0
        self.label = label
        self.passed = 0
        self.failed = 0
        self.errors = 0

    def execute(self, solution, sample):
        import time as _time
        print(f"  ⏳ {self.label} {self.count + 1}/{self.total}: {sample.id}...", flush=True)
        start = _time.monotonic()
        trace = self.inner.execute(solution, sample)
        elapsed = _time.monotonic() - start
        self.count += 1
        if trace.result == "PASS":
            self.passed += 1
            icon = "✓"
        elif trace.result == "FAIL":
            self.failed += 1
            icon = "✗"
        else:
            self.errors += 1
            icon = "⚠"
        print(f"  {icon} {sample.id} → {trace.result} ({elapsed:.0f}s)"
              f"  [累计 ✓{self.passed} ✗{self.failed} ⚠{self.errors}]",
              flush=True)
        return trace

    def evaluate(self, trace, expected):
        return self.inner.evaluate(trace, expected)

    def replay(self, solution, samples):
        return self.inner.replay(solution, samples)

    def runtime_provenance(self):
        return self.inner.runtime_provenance()


class DelegatedGatePolicy(AutoApprove):
    """用户代理人审批：Agent 按用户偏好自动审阅 G1 提案。

    偏好作为 System Prompt 的一部分，决策附上"基于用户偏好"的标签。
    所有决策落盘到 RunStore（通过 ReviewDecision 的 reviewer 字段）。
    """

    def __init__(self, preferences: str):
        super().__init__()
        self.preferences = preferences
        self._decision_log: list[dict] = []

    def review(self, request):
        import json as _json
        from agentfit.gates.human import GateType, ReviewDecision
        if request.gate != GateType.G1:
            return super().review(request)

        proposals = (request.evidence or {}).get("proposals", [])
        if not proposals:
            return ReviewDecision(True, "no proposals", "delegate:no-op")

        # 构建审批 prompt（用户偏好 + 提案摘要）
        proposal_summaries = []
        for i, p in enumerate(proposals, 1):
            summary = f"{i}. [{p.get('origin', '?')}] {p.get('semantic', '?')}"
            if p.get("reg_conflict"):
                summary += f"（⚔冲突：{p['reg_conflict']}）"
            evidence = p.get("evidence") or {}
            if evidence.get("type") == "samples":
                summary += f" 证据：{', '.join(evidence.get("sample_ids", [])[:3])}"
            elif evidence.get("type") == "metric":
                summary += f" 指标：{evidence.get("name")}={evidence.get("value")}"
            proposal_summaries.append(summary)

        prompt = f"""你是用户的审批代理人。用户写下的审批偏好如下：

{self.preferences}

以下是本轮训练产生的方案变更提案：

{chr(10).join(proposal_summaries)}

基于用户的偏好，判断是否批准这些提案。
只输出 JSON：{{"approved": true/false, "reason": "一句话理由"}}
"""

        # 调用 LLM（与 narrative 同款直连）
        decision = self._llm_review(prompt)
        if decision is None:
            # LLM 不可用 → 保守拒绝（回到手动）
            print("  ⚠️ 用户代理人不可用，回退到手动审批")
            return InteractiveGatePolicy().review(request)

        self._decision_log.append({
            "preferences": self.preferences,
            "proposals": proposal_summaries,
            "decision": decision,
        })
        approved = decision.get("approved", False)
        reason = decision.get("reason", "?")
        print(f"  🤖 用户代理人：{'✓ 批准' if approved else '✗ 拒绝'} — {reason}")
        return ReviewDecision(
            approved, f"delegate: {reason}", "delegate:user-simulator",
        )

    def _llm_review(self, prompt: str) -> dict | None:
        import os, json, urllib.request
        api_key = (os.environ.get("AGENTTEAMS_LLM_API_KEY")
                   or os.environ.get("DEEPSEEK_API_KEY"))
        if not api_key:
            return None
        payload = json.dumps({
            "model": "deepseek-v4-flash",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
        }).encode()
        req = urllib.request.Request(
            "https://api.deepseek.com/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {api_key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read())
            content = body["choices"][0]["message"]["content"].strip()
            # 提取 JSON
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(content)
        except Exception:
            return None


class InteractiveGatePolicy(AutoApprove):
    """交互式门禁策略：G1 提案实时呈现给用户审批。"""

    def review(self, request):
        from agentfit.gates.human import GateType, ReviewDecision
        if request.gate != GateType.G1:
            return super().review(request)

        proposals = (request.evidence or {}).get("proposals", [])
        if not proposals:
            return ReviewDecision(True, "no proposals", "interactive")

        _show("🔐 G1 · 方案变更审批")
        print(f"  本轮 {len(proposals)} 条提案：\n")
        for i, p in enumerate(proposals, 1):
            origin_label = "任务" if p.get("origin") == "task" else "正则"
            conflict = f" ⚔冲突:{p['reg_conflict']}" if p.get("reg_conflict") else ""
            print(f"  {i}. [{origin_label}] {p.get('semantic', '?')}{conflict}")
            evidence = p.get("evidence") or {}
            if evidence.get("type") == "samples":
                print(f"     证据：{', '.join(evidence.get('sample_ids', [])[:3])}")
            elif evidence.get("type") == "metric":
                print(f"     指标：{evidence.get('name')}={evidence.get('value')} 阈值={evidence.get('threshold')}")

        if _confirm(f"\n  批准全部 {len(proposals)} 条提案？"):
            return ReviewDecision(True, "user approved", "interactive-user")
        print("  （本轮空转，不应用变更）")
        return ReviewDecision(False, "user rejected", "interactive-user")


def main():
    parser = argparse.ArgumentParser(description="AgentFit 交互式训练入口")
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", default="deepseek-v4-flash")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"输出目录已存在: {args.output}")
    run_interactive(args.bundle, args.output, args.model)


if __name__ == "__main__":
    main()
