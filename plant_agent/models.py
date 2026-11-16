from __future__ import annotations

import copy
from typing import Any


DIAGRAM_KINDS = {
    "class",
    "sequence",
    "usecase",
    "activity",
    "state",
    "er",
    "component",
    "deployment",
    "flow",
    "dfd",
}

NODE_TYPES = {
    "class",
    "interface",
    "abstract",
    "actor",
    "usecase",
    "process",
    "decision",
    "entity",
    "database",
    "component",
    "service",
    "node",
    "state",
    "start",
    "end",
    "note",
    "participant",
    "external",
    "datastore",
}

EDGE_TYPES = {
    "association",
    "inheritance",
    "realization",
    "composition",
    "aggregation",
    "dependency",
    "flow",
    "sync",
    "async",
    "return",
    "include",
    "extend",
    "data",
}

THEMES = {"ocean", "paper", "dark"}


def blank_spec(title: str = "未命名图", kind: str = "class") -> dict[str, Any]:
    return {
        "title": title,
        "subtitle": "",
        "kind": kind,
        "theme": "ocean",
        "direction": "LR" if kind in {"class", "component", "deployment", "er"} else "TB",
        "nodes": [],
        "edges": [],
        "groups": [],
        "notes": [],
        "legend": True,
    }


def normalize_spec(raw: Any, default_kind: str | None = None) -> dict[str, Any]:
    """Return a stable, copyable diagram specification without mutating input."""
    if not isinstance(raw, dict):
        raise ValueError("图表规格必须是 JSON 对象")
    spec = copy.deepcopy(raw)
    kind = str(spec.get("kind") or default_kind or "class").strip().lower()
    if kind == "use-case":
        kind = "usecase"
    if kind == "flowchart":
        kind = "flow"
    spec["kind"] = kind if kind in DIAGRAM_KINDS else "class"
    spec["title"] = str(spec.get("title") or "未命名图").strip()[:120]
    spec["subtitle"] = str(spec.get("subtitle") or "").strip()[:240]
    theme = str(spec.get("theme") or "ocean").lower()
    spec["theme"] = theme if theme in THEMES else "ocean"
    direction = str(spec.get("direction") or "").upper()
    if direction not in {"LR", "TB"}:
        direction = "LR" if spec["kind"] in {"class", "component", "deployment", "er"} else "TB"
    spec["direction"] = direction
    spec["legend"] = bool(spec.get("legend", True))

    nodes: list[dict[str, Any]] = []
    for index, item in enumerate(spec.get("nodes") or []):
        if not isinstance(item, dict):
            continue
        node_id = str(item.get("id") or f"n{index + 1}").strip()
        if not node_id:
            node_id = f"n{index + 1}"
        node_type = str(item.get("type") or _default_node_type(spec["kind"])).lower()
        if node_type not in NODE_TYPES:
            node_type = _default_node_type(spec["kind"])
        node = dict(item)
        node["id"] = node_id
        node["label"] = str(item.get("label") or node_id).strip()[:160]
        node["type"] = node_type
        node["stereotype"] = str(item.get("stereotype") or "").strip()[:80]
        node["attributes"] = [str(x)[:180] for x in (item.get("attributes") or [])][:24]
        node["methods"] = [str(x)[:180] for x in (item.get("methods") or [])][:24]
        node["notes"] = str(item.get("notes") or "").strip()[:600]
        for coordinate in ("x", "y", "row", "column"):
            if coordinate in item:
                try:
                    node[coordinate] = float(item[coordinate])
                except (TypeError, ValueError):
                    node.pop(coordinate, None)
        nodes.append(node)
    spec["nodes"] = nodes

    edges: list[dict[str, Any]] = []
    for index, item in enumerate(spec.get("edges") or []):
        if not isinstance(item, dict):
            continue
        edge_type = str(item.get("type") or "association").lower()
        if edge_type not in EDGE_TYPES:
            edge_type = "association"
        edge = dict(item)
        edge["from"] = str(item.get("from") or "").strip()
        edge["to"] = str(item.get("to") or "").strip()
        edge["type"] = edge_type
        edge["label"] = str(item.get("label") or "").strip()[:120]
        edge["number"] = str(item.get("number") or "").strip()[:24]
        edge["guard"] = str(item.get("guard") or "").strip()[:100]
        edge["bidirectional"] = bool(item.get("bidirectional", False))
        try:
            edge["order"] = int(item.get("order", index + 1))
        except (TypeError, ValueError):
            edge["order"] = index + 1
        edges.append(edge)
    spec["edges"] = edges

    groups: list[dict[str, Any]] = []
    for index, item in enumerate(spec.get("groups") or []):
        if not isinstance(item, dict):
            continue
        groups.append(
            {
                **item,
                "id": str(item.get("id") or f"group{index + 1}")[:64],
                "label": str(item.get("label") or "系统边界")[:120],
                "nodes": [str(x) for x in (item.get("nodes") or [])],
            }
        )
    spec["groups"] = groups

    notes = []
    for item in spec.get("notes") or []:
        if isinstance(item, str):
            notes.append({"text": item[:600], "node": ""})
        elif isinstance(item, dict):
            notes.append(
                {
                    "text": str(item.get("text") or "")[:600],
                    "node": str(item.get("node") or ""),
                }
            )
    spec["notes"] = [item for item in notes if item["text"]]
    return spec


def _default_node_type(kind: str) -> str:
    return {
        "class": "class",
        "sequence": "participant",
        "usecase": "usecase",
        "activity": "process",
        "state": "state",
        "er": "entity",
        "component": "component",
        "deployment": "node",
        "dfd": "process",
        "flow": "process",
    }.get(kind, "process")
