"""四层依赖关系 SVG 图：L4→L3→L2→L1 连接线可视化。

服务端生成纯 SVG（禁用 JS 可见），节点=元素、连线=引用关系。
冻结=金色、训练=青色、不可达=虚线灰色。
"""
from __future__ import annotations

from typing import Any

# 布局参数
NODE_W = 130
NODE_H = 26
LAYER_GAP = 70
NODE_GAP = 10
PADDING = 20
SVG_WIDTH = 1200


def render_dependency_svg(solution_data: dict[str, Any]) -> str:
    """从 solution 数据生成四层依赖 SVG。"""
    atoms = solution_data.get("L1_atoms") or []
    tools = solution_data.get("L2_tools") or []
    knowledge = solution_data.get("L3_knowledge") or []
    agents = (solution_data.get("L4_topology") or {}).get("agents") or []

    # 过滤 superseded 知识
    active_knowledge = [k for k in knowledge if not k.get("superseded")]

    # 计算每层节点位置
    layers = [
        ("L4 · 拓扑", agents, lambda a: a.get("id", "?")),
        ("L3 · 知识", active_knowledge, lambda k: k.get("id", "?")),
        ("L2 · 能力", tools, lambda t: t.get("id", "?")),
        ("L1 · 原子", atoms, lambda a: a.get("id", "?")),
    ]

    max_count = max(len(items) for _, items, _ in layers) if layers else 0
    if max_count == 0:
        return ""

    svg_height = PADDING * 2 + len(layers) * (NODE_H + LAYER_GAP) + 30
    node_positions: dict[str, tuple[float, float]] = {}  # id -> (x, y)
    layer_rows: list[tuple[str, list[dict], float]] = []

    y = PADDING + 15
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SVG_WIDTH} {svg_height}" '
        f'width="100%" style="font-family:monospace;font-size:10px">',
        f'<defs>'
        f'<marker id="arrow" markerWidth="6" markerHeight="4" refX="5" refY="2" orient="auto">'
        f'<path d="M0,0 L6,2 L0,4" fill="#5a7a8e"/></marker></defs>',
    ]

    # 生成节点 + 记录位置
    for layer_idx, (label, items, name_fn) in enumerate(layers):
        count = len(items)
        total_width = count * NODE_W + (count - 1) * NODE_GAP if count > 0 else 0
        start_x = (SVG_WIDTH - total_width) / 2 if total_width < SVG_WIDTH else PADDING

        # 层标签
        svg_parts.append(
            f'<text x="{PADDING}" y="{y + NODE_H / 2 + 3}" fill="#718190" font-size="11" font-weight="700">{label}</text>')

        for i, item in enumerate(items):
            node_id = item.get("id", f"?{layer_idx}_{i}")
            x = start_x + i * (NODE_W + NODE_GAP)
            frozen = item.get("frozen", False)
            # 检查 L3 可达性
            unreachable = False
            if layer_idx == 1:  # L3
                all_uses = {u for a in agents for u in (a.get("uses") or [])}
                unreachable = node_id not in all_uses

            stroke = "#d6a43b" if frozen else "#74d0c7"
            fill = "rgba(214,164,59,0.08)" if frozen else "rgba(26,141,133,0.08)"
            dash = 'stroke-dasharray="4,3"' if unreachable else ""

            svg_parts.append(
                f'<rect x="{x}" y="{y}" width="{NODE_W}" height="{NODE_H}" rx="5" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="1.2" {dash}/>')
            # 截断过长名称
            display = name_fn(item)
            if len(display) > 18:
                display = display[:16] + "…"
            text_color = "#d6a43b" if frozen else "#74d0c7"
            if unreachable:
                text_color = "#5a7a8e"
            svg_parts.append(
                f'<text x="{x + NODE_W / 2}" y="{y + NODE_H / 2 + 3}" text-anchor="middle" '
                f'fill="{text_color}">{_esc(display)}</text>')

            node_positions[node_id] = (x + NODE_W / 2, y + NODE_H)  # bottom center
            # 也记录顶部中心（用于连线终点）
            node_positions[f"{node_id}__top"] = (x + NODE_W / 2, y)

        layer_rows.append((label, items, y))
        y += NODE_H + LAYER_GAP

    # 生成连接线（自顶向下）
    connections: list[tuple[str, str, str]] = []  # (from_id, to_id, color)

    # L4 → L3 (uses)
    for agent in agents:
        for used_id in (agent.get("uses") or []):
            if used_id in node_positions and used_id + "__top" in node_positions:
                frozen = any(k.get("id") == used_id and k.get("frozen") for k in active_knowledge)
                color = "#d6a43b" if frozen else "#74d0c7"
                connections.append((agent.get("id", ""), used_id, color))

    # L3 → L2 (dispatches_to + chain steps)
    for k in active_knowledge:
        targets = []
        if k.get("dispatches_to"):
            targets.append(k["dispatches_to"])
        for step in (k.get("steps") or []):
            if step.get("tool"):
                targets.append(step["tool"])
        for target in targets:
            if target in node_positions:
                frozen = k.get("frozen", False)
                color = "#d6a43b" if frozen else "#74d0c7"
                connections.append((k.get("id", ""), target, color))

    # L2 → L1 (wraps)
    for tool in tools:
        for wrapped in (tool.get("wraps") or []):
            if wrapped in node_positions:
                frozen = tool.get("frozen", False)
                color = "#d6a43b" if frozen else "#74d0c7"
                connections.append((tool.get("id", ""), wrapped, color))

    # 绘制贝塞尔曲线
    for from_id, to_id, color in connections:
        from_pos = node_positions.get(from_id)
        to_pos = node_positions.get(to_id + "__top")
        if from_pos is None or to_pos is None:
            continue
        fx, fy = from_pos
        tx, ty = to_pos
        mid_y = (fy + ty) / 2
        svg_parts.append(
            f'<path d="M{fx},{fy} C{fx},{mid_y} {tx},{mid_y} {tx},{ty}" '
            f'fill="none" stroke="{color}" stroke-width="1" opacity="0.5" '
            f'marker-end="url(#arrow)"/>')

    svg_parts.append("</svg>")
    return "".join(svg_parts)


def _esc(text: str) -> str:
    import html
    return html.escape(text, quote=True)
