from __future__ import annotations

import html
import math
from collections import defaultdict, deque
from typing import Any

from .models import normalize_spec


THEMES: dict[str, dict[str, str]] = {
    "ocean": {
        "bg": "#f6f8fb",
        "panel": "#ffffff",
        "panel_alt": "#eef4ff",
        "ink": "#172033",
        "muted": "#64748b",
        "line": "#94a3b8",
        "edge": "#53657d",
        "accent": "#2563eb",
        "accent_soft": "#dbeafe",
        "accent2": "#0f766e",
        "actor": "#0f766e",
        "group": "#dbeafe",
        "shadow": "#dce5f2",
    },
    "paper": {
        "bg": "#f7f3ea",
        "panel": "#fffdf8",
        "panel_alt": "#f3ead8",
        "ink": "#332d25",
        "muted": "#7c7062",
        "line": "#b7aa95",
        "edge": "#7b6d59",
        "accent": "#b45309",
        "accent_soft": "#ffedd5",
        "accent2": "#4d7c0f",
        "actor": "#4d7c0f",
        "group": "#efe2c9",
        "shadow": "#e7dcc9",
    },
    "dark": {
        "bg": "#101722",
        "panel": "#182333",
        "panel_alt": "#20314a",
        "ink": "#ecf3ff",
        "muted": "#a8b7cc",
        "line": "#536a86",
        "edge": "#9db1c9",
        "accent": "#6da8ff",
        "accent_soft": "#203b61",
        "accent2": "#55d6c2",
        "actor": "#55d6c2",
        "group": "#182f4c",
        "shadow": "#0a1018",
    },
}


def render_svg(spec: dict[str, Any]) -> str:
    spec = normalize_spec(spec)
    if spec.get("kind") == "sequence":
        return SVGRenderer(spec).render_sequence()
    return SVGRenderer(spec).render_graph()


class SVGRenderer:
    def __init__(self, spec: dict[str, Any]):
        self.spec = spec
        self.theme_key = spec.get("theme", "ocean")
        self.t = THEMES.get(self.theme_key, THEMES["ocean"])
        self.nodes = {node["id"]: node for node in spec.get("nodes", [])}
        self.width = 1000
        self.height = 700

    def render_graph(self) -> str:
        positions, content_w, content_h = self._layout_graph()
        legend_h = 66 if self.spec.get("legend", True) else 0
        notes = self.spec.get("notes") or []
        note_h = (len(notes) * 38 + 42) if notes else 0
        self.width = max(760, content_w + 100)
        self.height = max(520, content_h + 150 + max(legend_h, note_h))

        parts = [self._svg_open(), self._defs()]
        parts.append(self._heading())
        parts.append(self._render_groups(positions))

        for edge in self.spec.get("edges", []):
            parts.append(self._render_edge(edge, positions))
        for node in self.spec.get("nodes", []):
            if node["id"] not in positions:
                continue
            parts.append(self._render_node(node, positions[node["id"]]))

        if legend_h:
            parts.append(self._render_legend(self.height - legend_h - 18))
        if notes:
            parts.append(self._render_footnotes(self.height - note_h + 2))
        parts.append("</svg>")
        return "\n".join(parts)

    def render_sequence(self) -> str:
        nodes = self.spec.get("nodes", [])
        edges = sorted(self.spec.get("edges", []), key=lambda e: (e.get("order", 0), e.get("from", "")))
        step_h = 72
        top = 128
        positions: dict[str, dict[str, float]] = {}
        cursor = 64.0
        for node in nodes:
            width = max(142.0, min(238.0, 82.0 + len(node["label"]) * 10.0))
            positions[node["id"]] = {
                "x": cursor,
                "y": top,
                "w": width,
                "h": 50,
                "cx": cursor + width / 2,
            }
            cursor += width + 48
        self.width = max(780, cursor + 28)
        message_bottom = top + 82 + max(1, len(edges)) * step_h
        notes = self.spec.get("notes") or []
        note_h = len(notes) * 40 + (26 if notes else 0)
        self.height = max(520, message_bottom + 54 + note_h)
        bottom = self.height - note_h - 42

        parts = [self._svg_open(), self._defs(), self._heading()]
        for node in nodes:
            pos = positions[node["id"]]
            parts.append(
                f'<line x1="{pos["cx"]:.1f}" y1="{pos["y"] + pos["h"]:.1f}" '
                f'x2="{pos["cx"]:.1f}" y2="{bottom:.1f}" '
                f'stroke="{self.t["line"]}" stroke-width="1.3" stroke-dasharray="6 7"/>'
            )
            parts.append(
                f'<rect x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" width="{pos["w"]:.1f}" '
                f'height="{pos["h"]:.1f}" rx="9" fill="{self.t["panel"]}" '
                f'stroke="{self.t["accent"]}" stroke-width="1.5"/>'
            )
            parts.append(
                self._text_block(
                    pos["cx"], pos["y"] + 30, self._wrap(node["label"], 17, 2),
                    size=14, weight="600", anchor="middle", max_lines=2,
                )
            )

        for index, edge in enumerate(edges):
            if edge["from"] not in positions or edge["to"] not in positions:
                continue
            y = top + 94 + index * step_h
            x1 = positions[edge["from"]]["cx"]
            x2 = positions[edge["to"]]["cx"]
            dash = ' stroke-dasharray="7 6"' if edge["type"] in {"return", "async", "extend"} else ""
            marker = "m-open" if edge["type"] in {"async", "return"} else "m-arrow"
            if edge["from"] == edge["to"]:
                path = (
                    f"M {x1:.1f} {y:.1f} H {x1 + 58:.1f} V {y + 34:.1f} "
                    f"H {x1 + 8:.1f} V {y + 8:.1f}"
                )
                parts.append(
                    f'<path d="{path}" fill="none" stroke="{self.t["edge"]}" '
                    f'stroke-width="1.7"{dash} marker-end="url(#{marker})"/>'
                )
                label_x = x1 + 68
            else:
                direction = 1 if x2 > x1 else -1
                start = x1 + direction * 2
                end = x2 - direction * 9
                parts.append(
                    f'<line x1="{start:.1f}" y1="{y:.1f}" x2="{end:.1f}" y2="{y:.1f}" '
                    f'stroke="{self.t["edge"]}" stroke-width="1.7"{dash} '
                    f'marker-end="url(#{marker})"/>'
                )
                label_x = (x1 + x2) / 2
            label = " ".join(x for x in (edge.get("number", ""), edge.get("label", "")) if x)
            if edge.get("guard"):
                label += f" [{edge['guard']}]"
            if label:
                parts.append(self._edge_label(label_x, y - 10, label, max_width=220))

        if notes:
            parts.append(self._render_footnotes(self.height - note_h + 2))
        parts.append("</svg>")
        return "\n".join(parts)

    def _layout_graph(self) -> tuple[dict[str, dict[str, float]], float, float]:
        nodes = self.spec.get("nodes", [])
        levels = self._rank_nodes()
        buckets: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for node in nodes:
            level = int(node.get("row", levels.get(node["id"], 0)))
            buckets[level].append(node)

        positions: dict[str, dict[str, float]] = {}
        direction = self.spec.get("direction", "LR")
        gap_main = 105.0
        gap_cross = 54.0
        margin_x, margin_y = 58.0, 116.0

        sizes = {node["id"]: self._node_size(node) for node in nodes}
        ordered_levels = sorted(buckets)
        main_cursor = margin_y
        max_cross = 760.0

        if direction == "TB":
            level_widths = []
            for level in ordered_levels:
                width = sum(sizes[n["id"]][0] for n in buckets[level]) + gap_cross * max(0, len(buckets[level]) - 1)
                level_widths.append(width)
            max_cross = max(level_widths or [760])
            for level, level_width in zip(ordered_levels, level_widths):
                level_h = max((sizes[n["id"]][1] for n in buckets[level]), default=80)
                x = margin_x + (max_cross - level_width) / 2
                for node in buckets[level]:
                    w, h = sizes[node["id"]]
                    positions[node["id"]] = {"x": x, "y": main_cursor, "w": w, "h": h}
                    x += w + gap_cross
                main_cursor += level_h + gap_main
        else:
            level_heights = []
            for level in ordered_levels:
                height = sum(sizes[n["id"]][1] for n in buckets[level]) + gap_cross * max(0, len(buckets[level]) - 1)
                level_heights.append(height)
            max_cross = max(level_heights or [640])
            for level, level_height in zip(ordered_levels, level_heights):
                level_w = max((sizes[n["id"]][0] for n in buckets[level]), default=220)
                y = margin_y + (max_cross - level_height) / 2
                for node in buckets[level]:
                    w, h = sizes[node["id"]]
                    positions[node["id"]] = {"x": main_cursor, "y": y, "w": w, "h": h}
                    y += h + gap_cross
                main_cursor += level_w + gap_main

        # Explicit x/y coordinates are useful for hand-authored diagrams.
        for node in nodes:
            if "x" in node and "y" in node:
                pos = positions[node["id"]]
                pos["x"] = float(node["x"])
                pos["y"] = float(node["y"])

        if not positions:
            return {}, 760, 520
        min_x = min(p["x"] for p in positions.values())
        min_y = min(p["y"] for p in positions.values())
        max_x = max(p["x"] + p["w"] for p in positions.values())
        max_y = max(p["y"] + p["h"] for p in positions.values())
        content_w = max_x - min_x
        content_h = max_y - min_y
        if min_x < 30 or min_y < 100:
            dx = max(0, 58 - min_x)
            dy = max(0, 116 - min_y)
            for pos in positions.values():
                pos["x"] += dx
                pos["y"] += dy
            max_x += dx
            max_y += dy
        return positions, max_x - 58, max_y - 116

    def _rank_nodes(self) -> dict[str, int]:
        nodes = self.spec.get("nodes", [])
        ids = [node["id"] for node in nodes]
        adjacency: dict[str, list[str]] = {node_id: [] for node_id in ids}
        indegree = {node_id: 0 for node_id in ids}
        for edge in self.spec.get("edges", []):
            source, target = edge["from"], edge["to"]
            if source in adjacency and target in indegree and source != target:
                adjacency[source].append(target)
                indegree[target] += 1

        queue = deque(sorted(node_id for node_id in ids if indegree[node_id] == 0))
        levels = {node_id: 0 for node_id in ids}
        visited = set()
        while queue:
            source = queue.popleft()
            visited.add(source)
            for target in adjacency[source]:
                levels[target] = max(levels[target], levels[source] + 1)
                indegree[target] -= 1
                if indegree[target] == 0:
                    queue.append(target)

        remaining = [node_id for node_id in ids if node_id not in visited]
        if remaining:
            base = max((levels[node_id] for node_id in visited), default=-1) + 1
            for index, node_id in enumerate(remaining):
                levels[node_id] = base + index // 4
        return levels

    def _node_size(self, node: dict[str, Any]) -> tuple[float, float]:
        node_type = node["type"]
        if node_type == "actor":
            return 112, 124
        if node_type in {"start", "end"}:
            return 54, 54
        if node_type == "decision":
            return 164, 108
        if node_type == "usecase":
            return 218, 78
        if node_type in {"class", "interface", "abstract", "entity"}:
            line_count = len(node.get("attributes", [])) + len(node.get("methods", []))
            height = 82 + min(line_count, 12) * 20
            if node.get("stereotype") or node_type in {"interface", "abstract"}:
                height += 12
            return 246, max(128, height)
        if node_type in {"database", "datastore"}:
            return 190, 104
        if node_type in {"component", "service", "node", "external"}:
            return 216, 92
        return 220, 74

    def _render_groups(self, positions: dict[str, dict[str, float]]) -> str:
        parts = []
        for group in self.spec.get("groups", []):
            members = [positions[x] for x in group.get("nodes", []) if x in positions]
            if not members:
                continue
            x1 = min(m["x"] for m in members) - 24
            y1 = min(m["y"] for m in members) - 48
            x2 = max(m["x"] + m["w"] for m in members) + 24
            y2 = max(m["y"] + m["h"] for m in members) + 24
            parts.append(
                f'<rect x="{x1:.1f}" y="{y1:.1f}" width="{x2 - x1:.1f}" height="{y2 - y1:.1f}" '
                f'rx="18" fill="{self.t["group"]}" fill-opacity="0.48" '
                f'stroke="{self.t["accent"]}" stroke-opacity="0.52" stroke-width="1.4" '
                f'stroke-dasharray="7 6"/>'
            )
            parts.append(
                f'<text x="{x1 + 16:.1f}" y="{y1 + 24:.1f}" '
                f'font-size="12" font-weight="700" letter-spacing="0.06em" '
                f'fill="{self.t["accent"]}">{html.escape(group["label"])}</text>'
            )
        return "\n".join(parts)

    def _render_node(self, node: dict[str, Any], pos: dict[str, float]) -> str:
        x, y, w, h = pos["x"], pos["y"], pos["w"], pos["h"]
        node_type = node["type"]
        common = (
            f'<g class="node" data-node-id="{html.escape(node["id"])}" '
            f'data-node-type="{html.escape(node_type)}">'
        )
        if node_type == "actor":
            cx = x + w / 2
            top = y + 18
            body = (
                f'<circle cx="{cx:.1f}" cy="{top + 18:.1f}" r="17" fill="{self.t["panel"]}" '
                f'stroke="{self.t["actor"]}" stroke-width="2.2"/>'
                f'<line x1="{cx:.1f}" y1="{top + 35:.1f}" x2="{cx:.1f}" y2="{top + 73:.1f}" '
                f'stroke="{self.t["actor"]}" stroke-width="2.2"/>'
                f'<line x1="{cx - 27:.1f}" y1="{top + 50:.1f}" x2="{cx + 27:.1f}" y2="{top + 50:.1f}" '
                f'stroke="{self.t["actor"]}" stroke-width="2.2"/>'
                f'<line x1="{cx:.1f}" y1="{top + 73:.1f}" x2="{cx - 22:.1f}" y2="{top + 104:.1f}" '
                f'stroke="{self.t["actor"]}" stroke-width="2.2"/>'
                f'<line x1="{cx:.1f}" y1="{top + 73:.1f}" x2="{cx + 22:.1f}" y2="{top + 104:.1f}" '
                f'stroke="{self.t["actor"]}" stroke-width="2.2"/>'
            )
            text = self._text_block(
                cx, y + h - 3, self._wrap(node["label"], 12, 2),
                size=13, weight="600", anchor="middle", max_lines=2,
            )
            return common + body + text + "</g>"

        if node_type in {"start", "end"}:
            cx, cy = x + w / 2, y + h / 2
            fill = self.t["ink"] if node_type == "start" else self.t["panel"]
            inner = (
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="18" fill="{fill}" '
                f'stroke="{self.t["ink"]}" stroke-width="2"/>'
            )
            if node_type == "end":
                inner += (
                    f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="12" fill="{self.t["ink"]}"/>'
                )
            return common + inner + "</g>"

        if node_type == "decision":
            cx, cy = x + w / 2, y + h / 2
            points = (
                f"{cx:.1f},{y:.1f} {x + w:.1f},{cy:.1f} "
                f"{cx:.1f},{y + h:.1f} {x:.1f},{cy:.1f}"
            )
            body = (
                f'<polygon points="{points}" fill="{self.t["panel_alt"]}" '
                f'stroke="{self.t["accent"]}" stroke-width="1.8"/>'
            )
            text = self._text_block(
                cx, cy - 8, self._wrap(node["label"], 12, 3),
                size=13, weight="600", anchor="middle", max_lines=3,
            )
            return common + body + text + "</g>"

        if node_type == "usecase":
            cx, cy = x + w / 2, y + h / 2
            body = (
                f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{w / 2:.1f}" ry="{h / 2:.1f}" '
                f'fill="{self.t["panel"]}" stroke="{self.t["accent2"]}" stroke-width="1.8"/>'
            )
            text = self._text_block(
                cx, cy - 8, self._wrap(node["label"], 19, 2),
                size=13, weight="600", anchor="middle", max_lines=2,
            )
            return common + body + text + "</g>"

        if node_type in {"database", "datastore"}:
            rx = 13
            body = (
                f'<path d="M{x:.1f} {y + 15:.1f} V{y + h - 15:.1f} '
                f'C{x:.1f} {y + h + 3:.1f} {x + w:.1f} {y + h + 3:.1f} {x + w:.1f} {y + h - 15:.1f} '
                f'V{y + 15:.1f}" fill="{self.t["panel"]}" stroke="{self.t["accent2"]}" stroke-width="1.7"/>'
                f'<ellipse cx="{x + w / 2:.1f}" cy="{y + 15:.1f}" rx="{w / 2:.1f}" ry="{rx}" '
                f'fill="{self.t["panel_alt"]}" stroke="{self.t["accent2"]}" stroke-width="1.7"/>'
            )
            text = self._text_block(
                x + w / 2, y + h / 2 + 4, self._wrap(node["label"], 20, 2),
                size=13, weight="600", anchor="middle", max_lines=2,
            )
            return common + body + text + "</g>"

        if node_type in {"class", "interface", "abstract", "entity"}:
            return common + self._render_compartment_node(node, pos) + "</g>"

        if node_type in {"component", "service", "node", "external"}:
            return common + self._render_infra_node(node, pos) + "</g>"

        if node_type == "note":
            fold = 20
            body = (
                f'<path d="M{x:.1f} {y:.1f} H{x + w - fold:.1f} L{x + w:.1f} {y + fold:.1f} '
                f'V{y + h:.1f} H{x:.1f} Z" fill="{self.t["panel_alt"]}" '
                f'stroke="{self.t["line"]}" stroke-width="1.3"/>'
                f'<path d="M{x + w - fold:.1f} {y:.1f} V{y + fold:.1f} H{x + w:.1f}" '
                f'fill="none" stroke="{self.t["line"]}"/>'
            )
            text = self._text_block(
                x + 15, y + 28, self._wrap(node["label"], 24, 3),
                size=12, anchor="start", max_lines=3,
            )
            return common + body + text + "</g>"

        # Process/state-style rounded rectangle.
        radius = 26 if node_type == "state" else 12
        body = (
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{radius}" '
            f'fill="{self.t["panel"]}" stroke="{self.t["accent"]}" stroke-width="1.8" '
            f'filter="url(#soft-shadow)"/>'
        )
        text = self._text_block(
            x + w / 2, y + h / 2 - 8, self._wrap(node["label"], 20, 3),
            size=13, weight="600", anchor="middle", max_lines=3,
        )
        return common + body + text + "</g>"

    def _render_compartment_node(self, node: dict[str, Any], pos: dict[str, float]) -> str:
        x, y, w, h = pos["x"], pos["y"], pos["w"], pos["h"]
        stereotype = node.get("stereotype")
        if node["type"] == "interface" and not stereotype:
            stereotype = "<<interface>>"
        if node["type"] == "abstract" and not stereotype:
            stereotype = "<<abstract>>"
        header_h = 55 + (16 if stereotype else 0)
        attrs = node.get("attributes", [])
        methods = node.get("methods", [])
        attr_h = max(30, len(attrs) * 20 + 10)
        body = (
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="8" '
            f'fill="{self.t["panel"]}" stroke="{self.t["accent"]}" stroke-width="1.7" '
            f'filter="url(#soft-shadow)"/>'
            f'<line x1="{x:.1f}" y1="{y + header_h:.1f}" x2="{x + w:.1f}" y2="{y + header_h:.1f}" '
            f'stroke="{self.t["line"]}" stroke-width="1"/>'
        )
        if methods:
            method_sep = y + header_h + attr_h
            body += (
                f'<line x1="{x:.1f}" y1="{method_sep:.1f}" x2="{x + w:.1f}" y2="{method_sep:.1f}" '
                f'stroke="{self.t["line"]}" stroke-width="1"/>'
            )
        text_y = y + 23 if stereotype else y + 31
        if stereotype:
            body += (
                f'<text x="{x + w / 2:.1f}" y="{text_y:.1f}" text-anchor="middle" '
                f'font-size="11" font-weight="600" fill="{self.t["accent2"]}">'
                f'{self._fmt(stereotype)}</text>'
            )
            text_y += 19
        font_style = ' font-style="italic"' if node["type"] == "abstract" else ""
        body += (
            f'<text x="{x + w / 2:.1f}" y="{text_y:.1f}" text-anchor="middle" '
            f'font-size="14" font-weight="700" fill="{self.t["ink"]}"{font_style}>'
            f'{self._fmt(node["label"])}</text>'
        )
        for index, attr in enumerate(attrs[:12]):
            body += (
                f'<text x="{x + 14:.1f}" y="{y + header_h + 22 + index * 20:.1f}" '
                f'font-size="11.5" fill="{self.t["ink"]}">{self._fmt(attr[:36])}</text>'
            )
        for index, method in enumerate(methods[:12]):
            body += (
                f'<text x="{x + 14:.1f}" y="{y + header_h + attr_h + 22 + index * 20:.1f}" '
                f'font-size="11.5" fill="{self.t["muted"]}">{self._fmt(method[:36])}</text>'
            )
        return body

    def _render_infra_node(self, node: dict[str, Any], pos: dict[str, float]) -> str:
        x, y, w, h = pos["x"], pos["y"], pos["w"], pos["h"]
        stroke = self.t["accent2"] if node["type"] == "service" else self.t["accent"]
        body = (
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="10" '
            f'fill="{self.t["panel"]}" stroke="{stroke}" stroke-width="1.7" '
            f'filter="url(#soft-shadow)"/>'
        )
        icon_x, icon_y = x + 18, y + 19
        if node["type"] == "component":
            body += (
                f'<rect x="{icon_x:.1f}" y="{icon_y:.1f}" width="28" height="23" rx="3" '
                f'fill="{self.t["accent_soft"]}" stroke="{stroke}"/>'
                f'<rect x="{icon_x + 5:.1f}" y="{icon_y - 5:.1f}" width="13" height="8" '
                f'fill="{self.t["panel"]}" stroke="{stroke}"/>'
                f'<rect x="{icon_x + 18:.1f}" y="{icon_y - 5:.1f}" width="13" height="8" '
                f'fill="{self.t["panel"]}" stroke="{stroke}"/>'
            )
        elif node["type"] == "service":
            body += (
                f'<path d="M{icon_x + 3:.1f} {icon_y + 23:.1f} '
                f'C{icon_x - 6:.1f} {icon_y + 13:.1f} {icon_x + 1:.1f} {icon_y + 1:.1f} {icon_x + 14:.1f} {icon_y + 5:.1f} '
                f'C{icon_x + 22:.1f} {icon_y - 4:.1f} {icon_x + 35:.1f} {icon_y + 3:.1f} {icon_x + 34:.1f} {icon_y + 13:.1f} '
                f'C{icon_x + 43:.1f} {icon_y + 18:.1f} {icon_x + 36:.1f} {icon_y + 27:.1f} {icon_x + 25:.1f} {icon_y + 23:.1f} Z" '
                f'fill="{self.t["accent_soft"]}" stroke="{stroke}"/>'
            )
        elif node["type"] == "external":
            body += (
                f'<rect x="{icon_x:.1f}" y="{icon_y:.1f}" width="32" height="24" rx="3" '
                f'fill="{self.t["panel_alt"]}" stroke="{stroke}"/>'
                f'<path d="M{icon_x + 5:.1f} {icon_y + 6:.1f} H{icon_x + 27:.1f} '
                f'M{icon_x + 5:.1f} {icon_y + 12:.1f} H{icon_x + 22:.1f} '
                f'M{icon_x + 5:.1f} {icon_y + 18:.1f} H{icon_x + 25:.1f}" '
                f'stroke="{stroke}" stroke-width="1.2"/>'
            )
        else:
            body += (
                f'<path d="M{icon_x:.1f} {icon_y + 8:.1f} L{icon_x + 17:.1f} {icon_y:.1f} '
                f'L{icon_x + 34:.1f} {icon_y + 8:.1f} L{icon_x + 34:.1f} {icon_y + 26:.1f} '
                f'L{icon_x + 17:.1f} {icon_y + 34:.1f} L{icon_x:.1f} {icon_y + 26:.1f} Z" '
                f'fill="{self.t["accent_soft"]}" stroke="{stroke}"/>'
            )
        text = (
            f'<text x="{x + 63:.1f}" y="{y + 35:.1f}" font-size="13.5" font-weight="700" '
            f'fill="{self.t["ink"]}">{self._fmt(node["label"][:30])}</text>'
        )
        if node.get("stereotype"):
            text += (
                f'<text x="{x + 63:.1f}" y="{y + 56:.1f}" font-size="10.5" '
                f'fill="{self.t["accent2"]}">{self._fmt(node["stereotype"][:30])}</text>'
            )
        return body + text

    def _render_edge(self, edge: dict[str, Any], positions: dict[str, dict[str, float]]) -> str:
        source = positions.get(edge["from"])
        target = positions.get(edge["to"])
        if not source or not target:
            return ""
        edge_type = edge["type"]
        if edge["from"] == edge["to"]:
            cx, cy = source["x"] + source["w"], source["y"] + source["h"] / 2
            path = f"M{cx:.1f} {cy:.1f} C{cx + 58:.1f} {cy - 46:.1f} {cx + 58:.1f} {cy + 46:.1f} {cx:.1f} {cy + 18:.1f}"
            label_x, label_y = cx + 66, cy
        else:
            p1 = self._boundary_point(source, target)
            p2 = self._boundary_point(target, source)
            horizontal = abs(p1[0] - p2[0]) >= abs(p1[1] - p2[1])
            if horizontal:
                mid = (p1[0] + p2[0]) / 2
                path = f"M{p1[0]:.1f} {p1[1]:.1f} H{mid:.1f} V{p2[1]:.1f} H{p2[0]:.1f}"
                label_x, label_y = mid, (p1[1] + p2[1]) / 2 - 10
            else:
                mid = (p1[1] + p2[1]) / 2
                path = f"M{p1[0]:.1f} {p1[1]:.1f} V{mid:.1f} H{p2[0]:.1f} V{p2[1]:.1f}"
                label_x, label_y = (p1[0] + p2[0]) / 2, mid - 10
            if edge_type in {"dependency", "return", "include", "extend"}:
                path = f"M{p1[0]:.1f} {p1[1]:.1f} Q{(p1[0] + p2[0]) / 2:.1f} {(p1[1] + p2[1]) / 2 - 30:.1f} {p2[0]:.1f} {p2[1]:.1f}"
                label_x, label_y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2 - 34

        marker = {
            "inheritance": "m-triangle",
            "realization": "m-triangle",
            "composition": "m-diamond-filled",
            "aggregation": "m-diamond",
            "dependency": "m-open",
            "return": "m-open",
            "async": "m-open",
            "include": "m-open",
            "extend": "m-open",
            "data": "m-arrow",
            "sync": "m-arrow",
        }.get(edge_type, "m-arrow")
        dash_types = {"dependency", "realization", "return", "async", "include", "extend"}
        dash = ' stroke-dasharray="7 6"' if edge_type in dash_types else ""
        marker_start = ' marker-start="url(#m-arrow)"' if edge.get("bidirectional") else ""
        result = (
            f'<path d="{path}" fill="none" stroke="{self.t["edge"]}" stroke-width="1.65"'
            f'{dash} marker-end="url(#{marker})"{marker_start}/>'
        )
        label_parts = []
        if edge.get("number"):
            label_parts.append(edge["number"])
        if edge.get("label"):
            label_parts.append(edge["label"])
        if edge.get("guard"):
            label_parts.append(f"[{edge['guard']}]")
        if label_parts:
            result += self._edge_label(label_x, label_y, " ".join(label_parts), max_width=190)
        return result

    def _boundary_point(self, node: dict[str, float], toward: dict[str, float]) -> tuple[float, float]:
        cx = node["x"] + node["w"] / 2
        cy = node["y"] + node["h"] / 2
        tx = toward["x"] + toward["w"] / 2
        ty = toward["y"] + toward["h"] / 2
        dx, dy = tx - cx, ty - cy
        if dx == 0 and dy == 0:
            return cx, cy
        scale_x = (node["w"] / 2 + 5) / abs(dx) if dx else math.inf
        scale_y = (node["h"] / 2 + 5) / abs(dy) if dy else math.inf
        scale = min(scale_x, scale_y)
        return cx + dx * scale, cy + dy * scale

    def _render_legend(self, y: float) -> str:
        items = [
            ("inheritance", "继承"),
            ("realization", "实现"),
            ("composition", "组合"),
            ("aggregation", "聚合"),
            ("dependency", "依赖"),
        ]
        parts = [
            f'<g class="legend"><text x="58" y="{y:.1f}" font-size="11" font-weight="700" '
            f'fill="{self.t["muted"]}">关系图例</text>'
        ]
        x = 58.0
        for edge_type, label in items:
            marker = {
                "inheritance": "m-triangle",
                "realization": "m-triangle",
                "composition": "m-diamond-filled",
                "aggregation": "m-diamond",
                "dependency": "m-open",
            }[edge_type]
            dash = ' stroke-dasharray="5 4"' if edge_type in {"realization", "dependency"} else ""
            parts.append(
                f'<line x1="{x:.1f}" y1="{y + 25:.1f}" x2="{x + 37:.1f}" y2="{y + 25:.1f}" '
                f'stroke="{self.t["edge"]}" stroke-width="1.5"{dash} marker-end="url(#{marker})"/>'
                f'<text x="{x + 45:.1f}" y="{y + 29:.1f}" font-size="10.5" '
                f'fill="{self.t["muted"]}">{self._fmt(label)}</text>'
            )
            x += 122
        return "\n".join(parts) + "</g>"

    def _render_footnotes(self, y: float) -> str:
        parts = [
            f'<text x="58" y="{y:.1f}" font-size="11" font-weight="700" '
            f'fill="{self.t["muted"]}">说明</text>'
        ]
        for index, note in enumerate(self.spec.get("notes", [])):
            text_y = y + 24 + index * 38
            parts.append(
                f'<rect x="100" y="{text_y - 16:.1f}" width="{self.width - 158:.1f}" height="28" '
                f'rx="7" fill="{self.t["panel_alt"]}" stroke="{self.t["line"]}" stroke-opacity="0.45"/>'
                f'<text x="114" y="{text_y + 2:.1f}" font-size="11" '
                f'fill="{self.t["ink"]}">{self._fmt(note["text"][:150])}</text>'
            )
        return "\n".join(parts)

    def _heading(self) -> str:
        parts = [
            f'<text x="58" y="50" font-size="24" font-weight="750" '
            f'letter-spacing="-0.015em" fill="{self.t["ink"]}">{self._fmt(self.spec["title"])}</text>'
        ]
        if self.spec.get("subtitle"):
            parts.append(
                f'<text x="58" y="75" font-size="12.5" fill="{self.t["muted"]}">'
                f'{self._fmt(self.spec["subtitle"])}</text>'
            )
        kind_labels = {
            "class": "类图",
            "sequence": "时序图",
            "usecase": "用例图",
            "activity": "活动图",
            "state": "状态图",
            "er": "ER 图",
            "component": "组件图",
            "deployment": "部署图",
            "flow": "流程图",
            "dfd": "数据流图",
        }
        badge = kind_labels.get(self.spec["kind"], self.spec["kind"])
        badge_w = max(62, len(badge) * 15 + 24)
        parts.append(
            f'<rect x="{self.width - badge_w - 42:.1f}" y="29" width="{badge_w}" height="28" '
            f'rx="14" fill="{self.t["accent_soft"]}"/>'
            f'<text x="{self.width - 42 - badge_w / 2:.1f}" y="48" text-anchor="middle" '
            f'font-size="11.5" font-weight="700" fill="{self.t["accent"]}">{self._fmt(badge)}</text>'
        )
        return "\n".join(parts)

    def _svg_open(self) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}" role="img" '
            f'aria-label="{html.escape(self.spec["title"], quote=True)}">'
            f'<rect width="100%" height="100%" fill="{self.t["bg"]}"/>'
            f'<style>text{{font-family:"Microsoft YaHei","Segoe UI",Arial,sans-serif}}'
            f'.node{{shape-rendering:geometricPrecision}}</style>'
        )

    def _defs(self) -> str:
        edge = self.t["edge"]
        panel = self.t["panel"]
        shadows = ""
        if self.theme_key != "dark":
            shadows = (
                f'<filter id="soft-shadow" x="-20%" y="-20%" width="140%" height="150%">'
                f'<feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="{self.t["shadow"]}" '
                f'flood-opacity="0.65"/></filter>'
            )
        return (
            f"<defs>{shadows}"
            f'<marker id="m-arrow" markerWidth="10" markerHeight="10" refX="9" refY="5" '
            f'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{edge}"/></marker>'
            f'<marker id="m-open" markerWidth="11" markerHeight="11" refX="10" refY="5.5" '
            f'orient="auto-start-reverse"><path d="M0 1 L10 5.5 L0 10" fill="none" stroke="{edge}" '
            f'stroke-width="1.5"/></marker>'
            f'<marker id="m-triangle" markerWidth="14" markerHeight="14" refX="13" refY="7" '
            f'orient="auto-start-reverse"><path d="M1 1 L13 7 L1 13 Z" fill="{panel}" '
            f'stroke="{edge}" stroke-width="1.3"/></marker>'
            f'<marker id="m-diamond" markerWidth="18" markerHeight="14" refX="17" refY="7" '
            f'orient="auto-start-reverse"><path d="M1 7 L9 1 L17 7 L9 13 Z" fill="{panel}" '
            f'stroke="{edge}" stroke-width="1.3"/></marker>'
            f'<marker id="m-diamond-filled" markerWidth="18" markerHeight="14" refX="17" refY="7" '
            f'orient="auto-start-reverse"><path d="M1 7 L9 1 L17 7 L9 13 Z" fill="{edge}"/></marker>'
            f'<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">'
            f'<path d="M24 0H0V24" fill="none" stroke="{self.t["line"]}" stroke-opacity="0.08"/>'
            f"</pattern></defs>"
        )

    def _edge_label(self, x: float, y: float, text: str, max_width: int = 180) -> str:
        label = text[:34]
        width = min(max_width, max(28, len(label) * 7.2 + 14))
        return (
            f'<g class="edge-label"><rect x="{x - width / 2:.1f}" y="{y - 13:.1f}" '
            f'width="{width:.1f}" height="20" rx="6" fill="{self.t["bg"]}" fill-opacity="0.94"/>'
            f'<text x="{x:.1f}" y="{y + 1:.1f}" text-anchor="middle" font-size="10.5" '
            f'font-weight="600" fill="{self.t["muted"]}">{self._fmt(label)}</text></g>'
        )

    def _text_block(
        self,
        x: float,
        y: float,
        lines: list[str],
        *,
        size: float,
        weight: str = "400",
        anchor: str = "start",
        max_lines: int = 3,
    ) -> str:
        lines = lines[:max_lines]
        spans = []
        line_height = size * 1.35
        start_y = y - ((len(lines) - 1) * line_height) / 2
        for index, line in enumerate(lines):
            spans.append(
                f'<tspan x="{x:.1f}" y="{start_y + index * line_height:.1f}">{self._fmt(line)}</tspan>'
            )
        return (
            f'<text text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" '
            f'fill="{self.t["ink"]}">{"".join(spans)}</text>'
        )

    def _wrap(self, text: str, width: int, max_lines: int) -> list[str]:
        text = str(text).replace("<br>", "\n").replace("<br/>", "\n")
        lines: list[str] = []
        for paragraph in text.splitlines() or [text]:
            current = ""
            for char in paragraph:
                current += char
                if len(current) >= width:
                    cut = max(current.rfind(" "), current.rfind("，"), current.rfind("、"), current.rfind("/"))
                    if cut > width * 0.55:
                        lines.append(current[: cut + 1].rstrip())
                        current = current[cut + 1 :].lstrip()
                    else:
                        lines.append(current)
                        current = ""
            if current:
                lines.append(current)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = lines[-1][:-2] + "…"
        return lines

    @staticmethod
    def _fmt(value: Any) -> str:
        return html.escape(str(value), quote=True)
