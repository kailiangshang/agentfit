"""运行完成仪制（元层自举的落地）：

每次训练结束产出两样——训练结果（training_report.md/dashboard）+
对 AgentFit 自身（训练系统）的改进建议（本文件 meta_review.md）。

确定性推导，不编造：只从 RunStore 里真实存在的信号生成建议。
"""
from __future__ import annotations

from pathlib import Path

from ..store.run_store import RunStore


def _collect_signals(store: RunStore) -> dict:
    signals: dict = {"epochs": 0, "rolled_back": 0, "idle_epochs": 0, "updates": 0,
                     "attribution": {}, "low_confidence": 0, "loss_traces": 0,
                     "side_issues": 0, "eval_error_ratio": 0.0, "converged": None,
                     "budget_exceeded": None, "lambda_changes": []}
    for e in store.epochs():
        rec = store.load_json(f"epochs/epoch_{e:03d}.json")["entry"]
        signals["epochs"] += 1
        signals["rolled_back"] += 1 if rec.get("rolled_back") else 0
        signals["updates"] += len(rec.get("updates_applied", []))
        if not rec.get("updates_applied") and not rec.get("rolled_back"):
            signals["idle_epochs"] += 1
        prev = None
        lt_dir = store.root / "loss_traces" / f"epoch_{e:03d}"
        if lt_dir.is_dir():
            for p in lt_dir.glob("*.json"):
                lt = store.load_json(f"loss_traces/epoch_{e:03d}/{p.name}")
                signals["loss_traces"] += 1
                layer = lt["root_cause_layer"]
                signals["attribution"][layer] = signals["attribution"].get(layer, 0) + 1
                if (lt.get("confidence") or 1) < 0.7:
                    signals["low_confidence"] += 1
                signals["side_issues"] += len(lt.get("side_issues") or [])
    if signals["loss_traces"]:
        signals["eval_error_ratio"] = signals["attribution"].get("eval_error", 0) / signals["loss_traces"]
    if (store.root / "summary.json").exists():
        s = store.load_json("summary.json")
        signals["converged"] = s.get("converged")
        signals["budget_exceeded"] = s.get("budget_exceeded")
    return signals


def generate_meta_review(run_dir: str | Path) -> Path:
    store = RunStore(run_dir)
    sig = _collect_signals(store)
    suggestions: list[tuple[str, str]] = []   # (对象, 建议)

    # 1. 归因器（Attributor / attribution_skill）
    if sig["eval_error_ratio"] > 0.2:
        suggestions.append(("Attributor", f"eval_error 归因占 {sig['eval_error_ratio']:.0%}——"
                          "四层走查规则覆盖不足，扩展 attribution_skill 的失败模式识别"))
    if sig["loss_traces"] and sig["low_confidence"] / sig["loss_traces"] > 0.3:
        suggestions.append(("Attributor", "低置信度归因占比 >30%——反事实验证槽位需要 LLM 接入或阈值下调"))
    if sig["side_issues"] > sig["loss_traces"]:
        suggestions.append(("Attributor", "附带问题多于主归因——附带问题清理策略应进入下一轮训练目标"))

    # 2. 架构师（Architect / proposal_skill）
    if sig["rolled_back"] >= 2:
        suggestions.append(("Architect", f"{sig['rolled_back']} 次回滚——建议生成的保守度参数应调高（回归前自检）"))
    if sig["idle_epochs"] >= 2:
        suggestions.append(("Architect", f"{sig['idle_epochs']} 个空转轮（无建议无回滚）——"
                          "覆盖瓶颈可能在基础设施层（缺原子），考虑升级用户确认基础设施"))

    # 3. 编排者（Orchestrator / train_loop）
    if sig["converged"] is False:
        suggestions.append(("Orchestrator", "未收敛即停——检查 max_epochs/batch_size 配比或收敛窗口参数"))
    if sig["budget_exceeded"]:
        suggestions.append(("Orchestrator", "预算熔断触发——批次成本需前置估算（执行前预估而非事后统计）"))

    # 4. 正则与 λ（lambda_skill）
    first, last = None, None
    for e in store.epochs():
        rec = store.load_json(f"epochs/epoch_{e:03d}.json")["entry"]
        lam = rec.get("lambda_values") or {}
        if first is None:
            first = lam
        last = lam
    if first and last:
        for k in last:
            if abs(last[k] - first.get(k, last[k])) / max(0.01, first.get(k, last[k])) > 0.4:
                suggestions.append(("LambdaController", f"λ_{k[-1]} 累计变化 >40%——"
                                  "通过率与正则可能对抗，考虑生成 Level 2 人审建议"))

    lines = [f"# AgentFit 自身改进建议 · {store.root.name}", "",
             "> 运行完成仪制：训练结果见 training_report.md / dashboard.html；", "> "
             "本文件是对训练系统本身（元层）的建议——训练系统训练方案，运行经验反过来训练训练系统。", "",
             "## 运行信号", "",
             f"- 轮数 {sig['epochs']} · 提交更新 {sig['updates']} · 回滚 {sig['rolled_back']} · 空转 {sig['idle_epochs']}",
             f"- 归因分布 {sig['attribution']} · 低置信 {sig['low_confidence']} · 附带问题 {sig['side_issues']}", ""]
    if suggestions:
        lines += ["## 建议（按对象）", ""]
        for target, text in suggestions:
            lines.append(f"- **{target}**：{text}")
    else:
        lines += ["## 建议", "", "- 本轮无系统性问题信号——元层维持当前版本"]
    out = store.root / "meta_review.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out
