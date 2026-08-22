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

    from agentfit.materials.compiler import compile_material_bundle
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

    print("  ✓ G0 冻结完成，开始训练。")

    # ============ 4. 训练循环 ============
    from agentfit.agents.orchestrator import Orchestrator
    from agentfit.agents.team import build_team
    from agentfit.data.sample_pool import SamplePool
    from agentfit.executors.simulator import SimulatorExecutor
    from agentfit.models.config import TrainingConfig, AutoApprove
    from agentfit.models.manifest import SampleSetPurpose

    # 分离 adaptation / validation
    adaptation_manifest = compiled.sample_sets.by_purpose(SampleSetPurpose.ADAPTATION)
    adaptation_ids = {ref.sample_id for ref in adaptation_manifest.sample_refs}
    adaptation_samples = [s for s in samples if s.id in adaptation_ids]
    validation_samples = [s for s in samples if s.id not in adaptation_ids]

    training_cfg = bundle.get("training", {})
    config = TrainingConfig(
        batch_size=int(training_cfg.get("batch_size", len(adaptation_samples))),
        max_epochs=int(training_cfg.get("max_epochs", 3)),
        review_policy=InteractiveGatePolicy(),
    )

    orchestrator = Orchestrator(
        solution, SamplePool(adaptation_samples), SimulatorExecutor(), config,
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


class InteractiveGatePolicy(AutoApprove):
    """交互式门禁策略：G1 提案实时呈现给用户审批。"""

    def review(self, request):
        from agentfit.gates.human import GateType, ReviewDecision
        if request.gate != GateType.G1:
            return super().review(request)

        proposals = (request.payload or {}).get("proposals", [])
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
