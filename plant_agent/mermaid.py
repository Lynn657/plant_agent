from __future__ import annotations

import re
from typing import Any


def render_mermaid(spec: dict[str, Any]) -> str:
    kind = spec.get("kind")
    if kind == "class":
        body = _class_diagram(spec)
    elif kind == "sequence":
        body = _sequence_diagram(spec)
    elif kind == "state":
        body = _state_diagram(spec)
    elif kind == "er":
        body = _er_diagram(spec)
    else:
        body = _flow_diagram(spec)
    title = _mermaid_text(spec.get("title", "Diagram"))
    return f"---\ntitle: {title}\n---\n{body.rstrip()}\n"


def _class_diagram(spec: dict[str, Any]) -> str:
    lines = ["classDiagram", "    direction LR"]
    for node in spec["nodes"]:
        lines.append(f"    class {_id(node['id'])} {{")
        if node.get("stereotype"):
            lines.append(f"        {_member(node['stereotype'])}")
        elif node["type"] == "interface":
            lines.append("        <<interface>>")
        elif node["type"] == "abstract":
            lines.append("        <<abstract>>")
        for attr in node.get("attributes", []):
            lines.append(f"        {_member(attr)}")
        for method in node.get("methods", []):
            lines.append(f"        {_member(method)}")
        lines.append("    }")
    for edge in spec["edges"]:
        source, target = _id(edge["from"]), _id(edge["to"])
        label = _mermaid_text(edge.get("label", ""))
        relation = {
            "inheritance": f"{target} <|-- {source}",
            "realization": f"{target} <|.. {source}",
            "composition": f"{source} *-- {target}",
            "aggregation": f"{source} o-- {target}",
            "dependency": f"{source} ..> {target}",
            "flow": f"{source} --> {target}",
        }.get(edge["type"], f"{source} --> {target}")
        lines.append(f"    {relation}" + (f" : {label}" if label else ""))
    return "\n".join(lines)


def _sequence_diagram(spec: dict[str, Any]) -> str:
    lines = ["sequenceDiagram", "    autonumber"]
    for node in spec["nodes"]:
        label = _mermaid_text(node["label"])
        actor = "actor" if node["type"] == "actor" else "participant"
        lines.append(f"    {actor} {_id(node['id'])} as {label}")
    for edge in sorted(spec["edges"], key=lambda e: e.get("order", 0)):
        source, target = _id(edge["from"]), _id(edge["to"])
        arrow = {
            "return": "-->>",
            "async": "-)",
        }.get(edge["type"], "->>")
        label = " ".join(
            value for value in (edge.get("label", ""), f"[{edge.get('guard')}]" if edge.get("guard") else "") if value
        )
        lines.append(f"    {source}{arrow}{target}: {_mermaid_text(label)}")
    return "\n".join(lines)


def _state_diagram(spec: dict[str, Any]) -> str:
    lines = ["stateDiagram-v2", "    direction TB"]
    node_by_id = {node["id"]: node for node in spec["nodes"]}
    start_id = next((node["id"] for node in spec["nodes"] if node["type"] == "start"), None)
    if start_id:
        lines.append(f"    [*] --> {_id(start_id)}")
    for node in spec["nodes"]:
        if node["type"] not in {"start", "end"}:
            lines.append(f"    state {_mermaid_text(node['label'])} as {_id(node['id'])}")
    for edge in spec["edges"]:
        source = node_by_id.get(edge["from"], {})
        target = node_by_id.get(edge["to"], {})
        if source.get("type") == "start":
            continue
        if target.get("type") == "end":
            lines.append(f"    {_id(edge['from'])} --> [*] : {_mermaid_text(edge.get('label', ''))}")
        else:
            label = _mermaid_text(edge.get("label", ""))
            lines.append(f"    {_id(edge['from'])} --> {_id(edge['to'])}" + (f" : {label}" if label else ""))
    return "\n".join(lines)


def _er_diagram(spec: dict[str, Any]) -> str:
    lines = ["erDiagram", "    direction LR"]
    for node in spec["nodes"]:
        name = _id(node["id"])
        lines.append(f"    {name} {{")
        for attr in node.get("attributes", []):
            clean = re.sub(r"[^A-Za-z0-9_ ]", " ", attr).strip().replace(" ", "_")
            if not clean:
                clean = "field"
            lines.append(f"        string {clean[:48]}")
        if not node.get("attributes"):
            lines.append("        string id")
        lines.append("    }")
    for edge in spec["edges"]:
        label = _mermaid_text(edge.get("label") or "关联")
        lines.append(f"    {_id(edge['from'])} ||--o{{ {_id(edge['to'])} : {label}")
    return "\n".join(lines)


def _flow_diagram(spec: dict[str, Any]) -> str:
    direction = "LR" if spec.get("direction") == "LR" else "TB"
    lines = [f"flowchart {direction}"]
    for node in spec["nodes"]:
        node_id = _id(node["id"])
        label = _mermaid_text(node["label"])
        node_type = node["type"]
        if node_type in {"start", "end"}:
            shape = f"(({label}))"
        elif node_type == "decision":
            shape = f"{{{label}}}"
        elif node_type in {"class", "entity", "component", "service", "node"}:
            shape = f"[{label}]"
        elif node_type == "database":
            shape = f"[({label})]"
        elif node_type == "usecase":
            shape = f"({label})"
        elif node_type == "actor":
            shape = f"([{label}])"
        else:
            shape = f"[{label}]"
        lines.append(f"    {node_id}{shape}")
    for edge in spec["edges"]:
        label = " ".join(x for x in (edge.get("label", ""), edge.get("guard", "")) if x)
        arrow = "-.->" if edge["type"] in {"dependency", "include", "extend", "return"} else "-->"
        lines.append(
            f"    {_id(edge['from'])} {arrow} {_id(edge['to'])}"
            + (f"|{_mermaid_text(label)}|" if label else "")
        )
    for group in spec.get("groups", []):
        if not group.get("nodes"):
            continue
        lines.append(f'    subgraph {_id(group["id"])}["{_mermaid_text(group["label"])}"]')
        for node_id in group["nodes"]:
            lines.append(f"        {_id(node_id)}")
        lines.append("    end")
    return "\n".join(lines)


def _id(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_]", "_", str(value))
    if not clean:
        clean = "node"
    if clean[0].isdigit():
        clean = "n_" + clean
    return clean[:80]


def _member(value: str) -> str:
    return str(value).replace("{", "(").replace("}", ")").replace("\n", " ")[:140]


def _mermaid_text(value: str) -> str:
    return str(value).replace("\n", " ").replace('"', "'").replace("|", "/")[:180]
