"""Render a self-contained, script-safe Dashboard from one RunStore.

八区基本证据全部由静态 HTML 直接呈现（禁用 JavaScript 仍可完整阅读）；
内嵌 DATA 仅供后续交互增强，不承担内容渲染。训练曲线分开展示
adaptation Batch 指标与 validation 曲线（正本 §Dashboard 呈现合同）。
"""
from __future__ import annotations

import datetime
import html
import json
from pathlib import Path
from typing import Any

from ..store.run_store import RunStore


_STYLE = """
body{margin:0;background:#0b2236;color:#e8edf2;font:14px/1.5 -apple-system,'PingFang SC',sans-serif}
header{padding:24px 32px 12px;border-bottom:2px solid #28516d}header h1{margin:0;font-size:22px}
header .sub{color:#718190;font-family:monospace;font-size:12px;margin-top:4px}
main{padding:20px 32px 60px;display:grid;grid-template-columns:repeat(2,1fr);gap:16px;max-width:1400px;margin:auto}
section{min-width:0;overflow-x:auto;background:#132f47;border:2px solid #28516d;border-radius:14px;padding:16px 18px}section.wide{grid-column:1/-1}
h2{margin:0 0 10px;font-size:15px;color:#74d0c7;font-family:monospace}h3{margin:16px 0 8px;font-size:13px;color:#e8edf2}table{width:100%;border-collapse:collapse;font-size:12.5px}
th{color:#74d0c7;text-align:left;padding:5px 8px;border-bottom:1px solid #28516d}td{padding:5px 8px;border-bottom:1px solid #1d3d55;color:#a8c4d8}
.kpi{display:flex;gap:12px;flex-wrap:wrap}.kpi div{background:#1a3d4a;border:1px solid #1a8d85;border-radius:10px;padding:10px 14px;min-width:110px}
.kpi b{display:block;font-size:22px;color:#74d0c7;font-family:monospace}.kpi span{color:#718190;font-size:11px}
.bar{height:14px;background:#1a2d3f;border-radius:4px;overflow:hidden;display:inline-block;vertical-align:middle;width:180px}.bar i{display:block;height:100%;background:#74d0c7}
.tag{display:inline-block;border:1px solid #28516d;border-radius:6px;padding:1px 8px;margin:2px;font-size:11.5px;color:#a8c4d8}
.ok{color:#74d0c7}.bad{color:#f26b4b}.mut{color:#718190}.L1{color:#74a8c6}.L2{color:#4a90b8}.L3{color:#74d0c7}.L4{color:#d6a43b}
.status{margin-top:12px;font:600 13px/1.5 monospace;color:#a8c4d8}code{color:#74d0c7}
.runtime-line{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}.learning-story{margin-top:14px;padding-top:14px;border-top:1px solid #28516d}.learning-story h3{margin-top:0}.final-verdict{margin-top:10px;color:#a8c4d8}.flow{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.flow-step{min-width:0;background:#0f293e;border:1px solid #28516d;border-radius:10px;padding:12px;min-height:92px}.flow-step b{display:block;color:#74d0c7;margin-bottom:6px}.flow-step strong{display:block;font:700 17px/1.3 monospace;margin-bottom:5px}.flow-step span{overflow-wrap:anywhere;color:#a8c4d8;font-size:12px}
.evidence-wrap{overflow-x:auto}.result-pass{color:#74d0c7}.result-fail,.result-error{color:#f26b4b}.mono{font-family:monospace}
.frozen-element{display:inline-block;border:1px solid #d6a43b;border-radius:6px;padding:2px 8px;margin:2px;font-size:11.5px;color:#d6a43b;background:rgba(214,164,59,0.08)}
.trained-element{display:inline-block;border:1px solid #1a8d85;border-radius:6px;padding:2px 8px;margin:2px;font-size:11.5px;color:#74d0c7;background:rgba(26,141,133,0.08)}
legend-bar{padding:12px 32px;display:flex;flex-wrap:wrap;gap:8px 16px;border-bottom:1px solid #28516d;font-size:12px}
.legend-item{color:#718190}.legend-item b{margin-right:4px}
@media(max-width:900px){main{grid-template-columns:1fr;padding:14px}.flow{grid-template-columns:1fr}section{grid-column:1/-1}header{padding:18px 14px}}
"""


_LEGEND_HTML = """<div class="legend-bar">
<span class="legend-item"><b class="ok">PASS</b>执行成功且动作正确</span>
<span class="legend-item"><b class="bad">FAIL</b>执行完成但动作不对（方案问题→归因）</span>
<span class="legend-item"><b class="bad">ERROR</b>运行环境故障（非方案问题，不进归因）</span>
<span class="legend-item"><b class="mut">advisory</b>给用户的建议（非提案·非阻塞·不需审批）</span>
<span class="legend-item"><b class="L4">⚔冲突</b>任务提案与可维护性约束对抗</span>
<span class="legend-item"><b class="L4">🔒冻结</b>用户预指定（训练不可改，只出建议）</span>
<span class="legend-item"><b class="L3">来源:任务</b>失败样本证据驱动</span>
<span class="legend-item"><b class="L3">来源:正则</b>指标超阈驱动</span>
</div>"""

# ---------- 静态渲染小工具（全部经 html.escape，值即文本） ----------
class _Raw(str):
    """预构建的安全 HTML 片段标记；其余一切值按纯文本转义。"""


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _cell(value: Any) -> str:
    if isinstance(value, _Raw):
        return f"<td>{value}</td>"
    return f"<td>{_e(value)}</td>"


def _table(columns: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f"<th>{_e(c)}</th>" for c in columns)
    body = "".join("<tr>" + "".join(_cell(v) for v in row) + "</tr>" for row in rows)
    return f"<table><tr>{head}</tr>{body}</table>"


def _kpi(value: Any, label: str) -> str:
    return f"<div><b>{_e(value)}</b><span>{_e(label)}</span></div>"


def _kpis(items: list[tuple[Any, str]]) -> str:
    return '<div class="kpi">' + "".join(_kpi(v, label) for v, label in items) + "</div>"


def _badge(value: Any, cls: str = "tag") -> _Raw:
    return _Raw(f'<span class="{cls}">{_e(value)}</span>')


def _badges(values: list[Any]) -> _Raw:
    return _Raw("".join(_badge(v) for v in values))


def _bar(rate: float | None) -> _Raw:
    width = 0 if not isinstance(rate, (int, float)) else max(0, min(1, rate)) * 100
    text = "—" if not isinstance(rate, (int, float)) else f"{rate * 100:.0f}%"
    return _Raw(f'<span class="bar"><i style="width:{width:.0f}%"></i></span> {_e(text)}')


def _status(value: Any, good: bool = False, bad: bool = False) -> _Raw:
    cls = "ok" if good else "bad" if bad else "mut"
    return _badge(value, cls)


def _short_ref(value: Any) -> str:
    text = str(value or "")
    return f"{text[:12]}…" if text else "—"


def _outcome_counts(items: list[dict]) -> str:
    count = {"PASS": 0, "FAIL": 0, "ERROR": 0}
    for item in items:
        if item.get("result") in count:
            count[item["result"]] += 1
    return (f"{len(items)} 个样本 · {count['PASS']} 通过 / "
            f"{count['FAIL']} 失败 / {count['ERROR']} 运行错误")


_FAILURE_LABELS = {"missing_rule": "缺少路由规则", "tool_error": "工具调用错误",
                   "permission_denied": "权限不足",
                   "unreachable_knowledge": "知识未被拓扑引用",
                   "topology_mismatch": "拓扑能力不足"}
_ACTION_LABELS = {"add": "新增", "update": "更新", "remove": "删除", "modify": "修改",
                  "supersede": "下线"}


def _flow_step(title: str, value: Any, detail: Any) -> str:
    return (f'<div class="flow-step"><b>{_e(title)}</b>'
            f"<strong>{_e(value)}</strong><span>{_e(detail)}</span></div>")


def _render_training(payload: dict) -> str:
    sections: list[str] = []
    summary = payload.get("summary") or {}
    run = payload.get("run") or {}
    training_evidence = payload.get("training_evidence") or []
    forward = [item for item in training_evidence if item.get("phase") == "forward"]
    loss_items = [lt for values in (payload.get("loss_traces") or {}).values() for lt in values]
    first_loss = loss_items[0] if loss_items else {}
    committed = [c for t in (summary.get("transactions_committed") or []) for c in (t.get("changes") or [])]
    first_change = committed[0] if committed else {}
    final_evidence = payload.get("evaluation_evidence") or []

    # ① 运行概览
    overview_kpis: list[tuple[Any, str]] = []
    if summary:
        valid = isinstance(summary.get("final_pass_rate"), (int, float))
        cost_observed = not run.get("runtime_provenance", {}).get("cost_accounting") == "unavailable"
        overview_kpis.append((
            f"{summary['final_pass_rate'] * 100:.0f}%" if valid else "—",
            "训练批次通过率" if valid else "训练批次通过率 · 无有效方案评测"))
        overview_kpis.append((f"v{summary.get('final_solution_version')}", "方案版本"))
        overview_kpis.append((f"${summary.get('total_cost_usd')}" if cost_observed else "不可用", "总成本"))
        overview_kpis.append(("✓" if summary.get("log_chain_valid") else "✗", "哈希链"))
        overview_kpis.append((summary.get("stop_reason") or "进行中", "停止原因"))
    else:
        overview_kpis.append(("—", "无 summary（训练未完成）"))
    runtime = run.get("runtime_provenance") or {}
    runtime_line = '<div class="runtime-line">' + _badges([
        f"平台 {runtime.get('platform') or '未记录'}",
        f"模型 {runtime.get('model_ref') or '未记录'}",
        f"边界 {runtime.get('execution_boundary') or '未记录'}",
        f"模式 {runtime.get('binding_mode') or '未记录'}",
    ]) + "</div>"
    acceptance = payload.get("acceptance") or {}
    acceptance_state = ("PASS" if acceptance.get("met") is True
                        else "REJECT" if acceptance.get("met") is False else "PENDING")
    g3_state = ("APPROVED" if summary.get("delivery_approved") is True
                else "REJECTED" if summary.get("acceptance_met") is False else "PENDING")
    status_line = f'<div class="status">验收 {_e(acceptance_state)} · G3 {_e(g3_state)}</div>'
    story = ['<div class="learning-story"><h3>训练阶段发生了什么</h3>']
    if training_evidence:
        failure = _FAILURE_LABELS.get(first_loss.get("failure_mode"), first_loss.get("failure_mode") or "没有失败")
        story.append('<div class="flow">' + "".join([
            _flow_step("1 · 初始测试", _outcome_counts(forward), "用 adaptation 样本检验当前方案"),
            _flow_step("2 · 找到原因", failure,
                       f"{first_loss.get('sample_id') or '—'} · 归因到 {first_loss.get('root_cause_layer') or '未定位'}"),
            _flow_step("3 · 修改方案",
                       f"{first_change.get('layer') or '方案'} · {_ACTION_LABELS.get(first_change.get('action'), first_change.get('action') or '无变更')}",
                       first_change.get("element") or "没有产生变更"),
            _flow_step("4 · 再次测试", _outcome_counts(
                [item for item in training_evidence if item.get("phase") == "regression"]),
                "对回归池样本执行回归"),
        ]) + "</div>")
    else:
        story.append('<div class="mut">本次 RunStore 没有训练前后 Episode。</div>')
    if final_evidence:
        story.append(f'<div class="final-verdict">最终验收：{_e(_outcome_counts(final_evidence))}</div>')
    story.append("</div>")
    narrative = (payload.get("narrative") or {}).get("narrative")
    if narrative:
        story.append(f'<div class="final-verdict mut">{_e(narrative)}</div>')
    suggestions = payload.get("optimization_suggestions") or []
    if suggestions:
        story.append("<h3>整体优化建议（advisory · 非阻塞 · 决策权在用户）</h3>")
        story.append(_table(["建议", "涉及冻结元素"],
                            [[item.get("semantic") or "—",
                              ", ".join(item.get("frozen_elements") or []) or "—"]
                             for item in suggestions[:10]]))
    sections.append('<section class="wide"><h2>① 运行概览</h2>'
                    + _kpis(overview_kpis) + status_line + runtime_line + "".join(story) + "</section>")

    # ② 四集合验收
    evaluations = summary.get("evaluation_by_purpose") or {}
    criterion_by_purpose = {item.get("purpose"): item
                            for item in ((payload.get("objective") or {}).get("criteria") or [])}
    criteria_met = (acceptance or {}).get("criteria_met") or {}
    acceptance_rows = []
    for purpose in ("adaptation", "validation", "sealed_holdout", "stress_and_failure"):
        metric = evaluations.get(purpose) or {}
        criterion = criterion_by_purpose.get(purpose)
        rate = f"{metric['pass_rate'] * 100:.0f}%" if isinstance(metric.get("pass_rate"), (int, float)) else "—"
        threshold = (f"通过率≥{criterion['min_pass_rate'] * 100:.0f}%; ERROR≤{criterion.get('max_errors')}; "
                     f"成本≤${criterion.get('max_cost_usd')}; 风险≤{criterion.get('max_risk_events')}"
                     if criterion else "未定义")
        verdict = (_status("PASS", good=True) if criteria_met.get(purpose) is True
                   else _status("REJECT", bad=True) if criteria_met.get(purpose) is False
                   else _status("PENDING"))
        cost = ("不可用" if metric.get("cost_observed") is False
                else f"${metric['cost_usd']}" if isinstance(metric.get("cost_usd"), (int, float)) else "—")
        acceptance_rows.append([purpose, rate,
                                f"{metric.get('passed', '—')} / {metric.get('failed', '—')} / {metric.get('errors', '—')}",
                                cost, metric.get("risk_events", 0), threshold, verdict])
    acceptance_html = '<section class="wide"><h2>② 四集合验收</h2>' + _table(
        ["集合", "通过率", "PASS / FAIL / ERROR", "成本", "风险事件", "验收门槛", "结果"],
        acceptance_rows)
    failures = (acceptance or {}).get("failures") or []
    if failures:
        acceptance_html += f'<div class="bad">未满足条件：{_e(" · ".join(failures))}</div>'
    acceptance_html += "<h3>逐样本结果</h3>"
    if final_evidence:
        rows = [[item.get("purpose") or "—", item.get("sample_id"),
                 _status(item.get("result"), good=item.get("result") == "PASS",
                         bad=item.get("result") != "PASS"),
                 item.get("run_index"),
                 item.get("error_code") or " → ".join(item.get("route") or []) or "—",
                 _Raw(f"<code>{_e(_short_ref(item.get('candidate_ref')))}</code>")]
                for item in final_evidence]
        acceptance_html += '<div class="evidence-wrap">' + _table(
            ["集合", "样本", "结果", "RunIndex", "实际路径 / 运行错误", "Candidate"], rows) + "</div>"
    else:
        acceptance_html += '<div class="mut">最终评价尚未运行；当前只展示 adaptation 学习证据。</div>'
    sections.append(acceptance_html + "</section>")

    # ③ 材料与四层映射
    versions = sorted((payload.get("solutions") or {}).keys(), key=lambda v: int(v))
    first = (payload.get("solutions") or {}).get(versions[0]) if versions else None
    mapping_html = "<section><h2>③ 材料与四层映射（初始方案）</h2>"
    if first:
        solution = first.get("solution") or {}
        def _element_badge(item: dict, extra: str = "") -> _Raw:
            frozen = item.get("frozen", False)
            marker = "🔒" if frozen else "✦"
            cls = "frozen-element" if frozen else "trained-element"
            return _Raw(f'<span class="{cls}">{_e(marker)} {_e(item.get("id", "?"))}'
                        + (f"（{_e(extra)}）" if extra else "") + "</span>")

        frozen_count = sum(1 for pool in ("L1_atoms", "L2_tools", "L3_knowledge")
                          for item in (solution.get(pool) or []) if item.get("frozen"))
        trained_count = (len(solution.get("L1_atoms") or []) + len(solution.get("L2_tools") or [])
                        + len(solution.get("L3_knowledge") or []) - frozen_count)
        mapping_html += f'<div class="mut" style="margin-bottom:8px">🔒 用户预指定 {frozen_count} 个 · ✦ 训练产生 {trained_count} 个</div>'

        mapping_html += _table(["层", "元素数", "清单"], [
            ["L1 Solid", len(solution.get("L1_atoms") or []),
             _Raw("".join(str(_element_badge(item, f"{item.get('domain', 'data_interface')}·{item.get('type')}"))
                      for item in solution.get("L1_atoms") or []))],
            ["L2 能力", len(solution.get("L2_tools") or []),
             _Raw("".join(str(_element_badge(item, ", ".join(item.get("wraps") or [])))
                      for item in solution.get("L2_tools") or []))],
            ["L3 知识", len(solution.get("L3_knowledge") or []),
             _Raw("".join(str(_element_badge(item, item.get("type", "")))
                      for item in solution.get("L3_knowledge") or []))],
            ["L4 拓扑", len((solution.get("L4_topology") or {}).get("agents") or []),
             _Raw("".join(str(_element_badge(item, item.get("role", "")))
                      for item in (solution.get("L4_topology") or {}).get("agents") or []))],
        ])
    sections.append(mapping_html + "</section>")

    # ④ 样本与聚类分组
    samples_html = "<section><h2>④ 样本与聚类分组</h2>"
    task_samples = payload.get("task_samples") or {}
    if task_samples.get("samples"):
        groups: dict[str, list[str]] = {}
        for sample in task_samples["samples"]:
            key = ", ".join(f"{k}={v}" for k, v in sorted((sample.get("input_data") or {}).items()))
            groups.setdefault(key, []).append(sample.get("id"))
        rows = [[_badge(key, "mut"), len(ids),
                 ", ".join(ids[:4]) + (" …" if len(ids) > 4 else "")]
                for key, ids in groups.items()]
        if payload.get("sample_sets"):
            rows.append(["集合", "—", " · ".join(
                f"{m.get('purpose')} × {len(m.get('sample_refs') or [])}"
                for m in (payload["sample_sets"].get("manifests") or []))])
        samples_html += _table(["特征签名（聚类）", "样本数", "示例"], rows)
    sections.append(samples_html + "</section>")

    # ⑤ 训练曲线：adaptation Batch 指标与 validation 曲线分列（不混成一条通过率）
    curve_html = "<section><h2>⑤ 训练曲线</h2><h3>Epoch 汇总（adaptation / validation 分列）</h3>"
    epoch_rows = []
    for record in payload.get("epochs") or []:
        entry = record.get("entry") or {}
        adaptation_rate = entry.get("adaptation_pass_rate")
        validation_rate = entry.get("pass_rate")
        had_validation = isinstance((entry.get("validation") or {}).get("pass_rate"), (int, float)) \
            if isinstance(entry.get("validation"), dict) else isinstance(validation_rate, (int, float)) and bool(payload.get("validation"))
        epoch_rows.append([
            entry.get("epoch"),
            _bar(adaptation_rate),
            _bar(validation_rate) if payload.get("validation") else _Raw('<span class="mut">未运行</span>'),
            f"${entry.get('cost_usd', 0):.3f}",
            "/".join(f"{v:.2f}" for v in (entry.get("lambda_values") or {}).values()),
            len(entry.get("updates_applied") or []),
            _status("是", bad=True) if entry.get("rolled_back") else _status("否", good=True),
        ])
    curve_html += _table(["epoch", "adaptation 通过率", "validation 通过率", "成本", "λ(L1/L2/L3/L4)", "更新数", "回滚"],
                         epoch_rows)
    steps = payload.get("steps") or []
    if steps:
        curve_html += "<h3>adaptation Batch（Step 级指标）</h3>"
        curve_html += _table(
            ["epoch.step", "批大小", "通过/失败", "运行错误", "建议", "应用", "回滚", "成本"],
            [[f"{s.get('epoch')}.{s.get('step_index')}", s.get("batch_size"),
              f"{s.get('passed')}/{s.get('failed')}", s.get("execution_errors"),
              s.get("proposals"), s.get("applied"),
              _status("是", bad=True) if s.get("rolled_back") else _status("否", good=True),
              f"${s.get('cost_usd', 0):.3f}"] for s in steps])
    replay = payload.get("train_replay") or []
    if replay:
        curve_html += "<h3>train_replay（诊断重放，单独核算）</h3>"
        curve_html += _table(["次数", "total", "passed", "failed", "errors", "通过率", "成本"],
                             [[i + 1, r.get("total"), r.get("passed"), r.get("failed"),
                               r.get("errors"), _bar(r.get("pass_rate")), f"${r.get('cost_usd', 0):.3f}"]
                              for i, r in enumerate(replay)])
    sections.append(curve_html + "</section>")

    # ⑥ 损失归因全景
    layer_count: dict[str, int] = {}
    for values in (payload.get("loss_traces") or {}).values():
        for item in values:
            layer_count[item.get("root_cause_layer")] = layer_count.get(item.get("root_cause_layer"), 0) + 1
    total_losses = sum(layer_count.values())
    losses_html = "<section><h2>⑥ 损失归因全景</h2>" + _kpis([
        (count, f"{layer} {count / total_losses * 100:.0f}%") for layer, count in layer_count.items()
    ] or [("—", "无失败归因")])
    loss_rows = []
    solutions_payload = payload.get("solutions") or {}
    _versions = sorted(solutions_payload.keys(), key=lambda v: int(v)) if solutions_payload else []
    _last_solution = (solutions_payload.get(_versions[-1]) or {}).get("solution") or {} if _versions else {}
    _desc_by_id = {item.get("id"): item.get("description") or ""
                   for pool in (_last_solution.get("L1_atoms") or [], _last_solution.get("L2_tools") or [],
                                _last_solution.get("L3_knowledge") or [])
                   for item in pool}
    for epoch, values in (payload.get("loss_traces") or {}).items():
        for item in values:
            layer = item.get("root_cause_layer")
            element_id = item.get("root_cause_element")
            element_semantic = _desc_by_id.get(element_id, "")
            loss_rows.append([f"e{epoch}", item.get("sample_id"),
                              _badge(layer, layer if layer in ("L1", "L2", "L3", "L4") else "mut"),
                              item.get("failure_mode"),
                              f"{element_id}" + (f"（{element_semantic}）" if element_semantic else ""),
                              f"{item.get('confidence', 1):.2f}",
                              f"⚠ {len(item.get('side_issues') or [])} 附带"
                              if item.get("side_issues") else "-"])
    losses_html += _table(["轮", "样本", "层", "模式", "元素", "置信度", "附带问题"], loss_rows[:40])
    sections.append(losses_html + "</section>")

    # ⑦ L1-L4 方案证据与版本演化
    evolution_html = "<section><h2>⑦ L1-L4 方案证据与版本演化</h2>"
    solutions = payload.get("solutions") or {}
    last = solutions.get(versions[-1]) if versions else None
    if last:
        evolution_html += _table(["版本", "演化说明"],
                                 [[f"v{v}", solutions[v].get("note") or "-"] for v in versions])
        solution = last.get("solution") or {}
        rules = [item for item in solution.get("L3_knowledge") or []
                 if item.get("type") == "routing_rule" and not item.get("superseded")]
        evolution_html += _table(["L3 路由规则（当前）"],
                                 [[f"{item.get('id')} {item.get('condition') or ''} → {item.get('dispatches_to') or ''}"
                                   + (f" · {item.get('description')}" if item.get("description") else "")
                                   + (" · 🔒冻结" if item.get("frozen") else "")]
                                  for item in rules])
        evolution_html += _table(["L4 Agent"],
                                 [[f"{item.get('id')} ({item.get('role')}) · 引用 {len(item.get('uses') or [])} 条知识"
                                   + (" · 🔒冻结" if item.get("frozen") else "")]
                                  for item in (solution.get("L4_topology") or {}).get("agents") or []])
    sections.append(evolution_html + "</section>")

    # ⑧ 事务与中间链路
    transactions_html = "<section><h2>⑧ 事务与中间链路</h2>"
    tx = (summary.get("transactions_committed") or []) + (summary.get("transactions_rolled_back") or [])
    transactions_html += _table(
        ["状态", "来源", "变更摘要（人话）", "层·动作·元素", "理由"],
        [[_status("回滚", bad=True) if t.get("rolled_back") else _status("提交", good=True),
          _status("正则", good=True) if c.get("origin") == "regularization" else _status("任务", good=True),
          c.get("semantic") or "—",
          f"{c.get('layer')}·{c.get('action')}·{c.get('element')}"
          + (f" ⚔冲突:{c['reg_conflict']}" if c.get("reg_conflict") else ""),
          str(c.get("reason") or "")[:40]]
         for t in tx for c in (t.get("changes") or [])])
    transactions_html += "<h3>消息因果链（按轮）</h3>"
    transactions_html += _table(
        ["轮", "消息数", "类型流"],
        [[f"e{epoch}", len(items),
          " · ".join(i.get("type", "") for i in items if i.get("dir") == "task")[:80]]
         for epoch, items in (payload.get("messages") or {}).items()])

    # Agent 协同明细（谁用哪个 Skill 在哪步做了什么）
    activity = payload.get("agent_activity") or []
    if activity:
        transactions_html += "<h3>Agent 协同明细（Skill 调用记录）</h3>"
        rows = []
        for epoch_activities in activity:
            for act in epoch_activities:
                rows.append([
                    f"e{act.get('epoch')}.{act.get('step')}",
                    _badge(act.get("agent", "?"), "L3"),
                    f"{act.get('skill', '?')}@{act.get('skill_version', '?')[:8]}",
                    act.get("input_summary", ""),
                    act.get("output_summary", ""),
                ])
        transactions_html += _table(
            ["轮.步", "Agent", "Skill@版本", "输入", "产出"], rows)

    sections.append(transactions_html + "</section>")

    return "<main>" + "".join(sections) + "</main>"


_EXTERNAL_BODY = """<main><section class="wide"><h2>外部评价证据 · 评价概览</h2><div class="kpi" id="kpis"></div></section>
<section><h2>候选与证据边界</h2><div id="candidate"></div></section><section><h2>逐条证据链</h2><div id="records"></div></section></main>"""

_DOM_HELPERS = r"""
function el(tag, cls, text){const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined&&text!==null)node.textContent=String(text);return node;}
function add(parent,...children){children.flat().forEach(child=>{if(child!==undefined&&child!==null)parent.appendChild(child instanceof Node?child:document.createTextNode(String(child)));});return parent;}
function table(columns,rows){const out=el('table');const head=el('tr');columns.forEach(value=>head.appendChild(el('th',null,value)));out.appendChild(head);rows.forEach(row=>{const tr=el('tr');row.forEach(value=>{const td=el('td');add(td,value);tr.appendChild(td);});out.appendChild(tr);});return out;}
function kpi(value,label){const box=el('div');add(box,el('b',null,value),el('span',null,label));return box;}
"""

_EXTERNAL_SCRIPT = r"""
const summary=DATA.summary||{};const evaluation=summary.evaluation||{};const kpis=document.getElementById('kpis');[['通过率',(Number(evaluation.pass_rate||0)*100).toFixed(0)+'%'],['PASS/FAIL/ERROR',(evaluation.passed||0)+'/'+(evaluation.failed||0)+'/'+(evaluation.errors||0)],['成本','$'+(evaluation.cost_usd||0)],['风险事件',evaluation.risk_events||0],['证据记录',summary.evidence_records||0]].forEach(item=>kpis.appendChild(kpi(item[1],item[0])));
const candidate=document.getElementById('candidate');const first=el('p');add(first,'CandidateRef: ',code(summary.candidate_ref||''));const second=el('p',null,'Provenance: '+(DATA.candidate_manifest&&DATA.candidate_manifest.provenance_complete?'完整':'不完整，禁止扩大结论'));const third=el('p');add(third,'证据链根: ',code(summary.evidence_chain_root||''));add(candidate,first,second,third);
const rows=(DATA.external_evidence||[]).map(record=>[record.source_index,record.sample_ref.sample_id,record.run_index,record.result,code(String(record.content_hash||'').slice(0,16)+'…')]);document.getElementById('records').appendChild(table(['source','sample','run','result','hash'],rows));
"""


def _script_json(value: Any) -> str:
    """Serialize JSON so data cannot close the containing script element."""
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _document(*, run_name: str, generated_at: str, body: str,
              payload_json: str, script: str = "", legend: str = "") -> str:
    safe_name = html.escape(run_name, quote=True)
    safe_generated = html.escape(generated_at, quote=True)
    script_block = (f"<script>\nconst DATA = {payload_json};\n{script}</script>") if script or payload_json else ""
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>AgentFit Dashboard · {safe_name}</title><style>{_STYLE}</style></head><body>
<header><h1>AgentFit 训练全景 · {safe_name}</h1><div class="sub">方案不是设计出来的，是训练出来的 · 生成于 {safe_generated}</div></header>
{legend}{body}{script_block}</body></html>"""


def generate_dashboard(run_dir: str | Path, output: str | Path | None = None) -> Path:
    store = RunStore(run_dir)
    payload = store.dashboard_payload()
    run_name = str(payload.get("run", {}).get("scenario", Path(run_dir).name))
    generated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    is_external = (payload.get("run") or {}).get("run_kind") == "external_evaluation"
    if is_external:
        document = _document(
            run_name=run_name, generated_at=generated_at, body=_EXTERNAL_BODY,
            payload_json=_script_json(payload),
            script=_DOM_HELPERS + _EXTERNAL_SCRIPT,
        )
    else:
        # 八区静态直出；DATA 仅供后续交互增强（禁用 JS 仍可完整阅读）
        document = _document(
            run_name=run_name, generated_at=generated_at,
            body=_render_training(payload),
            payload_json=_script_json(payload),
            legend=_LEGEND_HTML,
        )
    out = Path(output) if output else Path(run_dir) / "dashboard.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(document, encoding="utf-8")
    return out
