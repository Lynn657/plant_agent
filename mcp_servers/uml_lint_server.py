#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from plant_agent.validation import validate_and_normalize  # noqa: E402


TOOLS = [
    {
        "name": "validate_spec",
        "description": "审查 PlantAgent DiagramSpec 的节点、关系、分组和 UML 结构完整性。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spec_json": {"type": "string", "description": "DiagramSpec JSON 字符串"}
            },
            "required": ["spec_json"],
        },
    },
    {
        "name": "conventions",
        "description": "返回 UML 与设计模式绘图的核心约定。",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def send(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def tool_result(text: str, is_error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def validate_spec(spec_json: str) -> str:
    try:
        raw = json.loads(spec_json)
    except json.JSONDecodeError as exc:
        return json.dumps({"ok": False, "errors": [f"JSON 错误: {exc}"], "warnings": []}, ensure_ascii=False)
    spec, errors, warnings = validate_and_normalize(raw)
    nodes = spec.get("nodes", [])
    edges = spec.get("edges", [])
    connected = {edge.get("from") for edge in edges} | {edge.get("to") for edge in edges}
    isolated = [node.get("id") for node in nodes if node.get("id") not in connected]
    if len(nodes) > 1 and isolated:
        warnings.append("孤立节点: " + ", ".join(str(item) for item in isolated))
    if spec.get("kind") == "class":
        interfaces = sum(node.get("type") in {"interface", "abstract"} for node in nodes)
        if "模式" in spec.get("title", "") and interfaces == 0:
            warnings.append("设计模式类图建议显式区分接口/抽象角色")
    return json.dumps(
        {
            "ok": not errors,
            "kind": spec.get("kind"),
            "nodes": len(nodes),
            "edges": len(edges),
            "errors": errors,
            "warnings": warnings,
            "score": max(0, 100 - len(errors) * 25 - len(warnings) * 5),
        },
        ensure_ascii=False,
    )


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = request.get("method")
        request_id = request.get("id")
        if method == "initialize":
            send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {"listChanged": False}},
                        "serverInfo": {"name": "uml-lint", "version": "1.0.0"},
                    },
                }
            )
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            params = request.get("params") or {}
            name = params.get("name")
            args = params.get("arguments") or {}
            try:
                if name == "validate_spec":
                    content = tool_result(validate_spec(str(args.get("spec_json") or "")))
                elif name == "conventions":
                    content = tool_result(
                        "1) 先明确系统边界；2) 关系方向从源指向目标；"
                        "3) 继承/实现箭头指向抽象端；4) 组合与聚合从整体指向部分；"
                        "5) 时序图按 order 排列；6) 每张图只回答一个主要问题。"
                    )
                else:
                    content = tool_result(f"未知工具: {name}", True)
            except Exception as exc:
                content = tool_result(f"{type(exc).__name__}: {exc}", True)
            send({"jsonrpc": "2.0", "id": request_id, "result": content})
        elif request_id is not None:
            send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }
            )


if __name__ == "__main__":
    main()
