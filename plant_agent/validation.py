from __future__ import annotations

from collections import Counter
from typing import Any

from .models import DIAGRAM_KINDS, EDGE_TYPES, NODE_TYPES, normalize_spec


def validate_and_normalize(raw: Any, default_kind: str | None = None) -> tuple[dict[str, Any], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        spec = normalize_spec(raw, default_kind)
    except Exception as exc:
        return normalize_spec({"title": "无效图表", "kind": default_kind or "class"}), [str(exc)], warnings

    if spec["kind"] not in DIAGRAM_KINDS:
        errors.append(f"不支持的图表类型: {spec['kind']}")
    nodes = spec["nodes"]
    if not nodes:
        errors.append("图表至少需要一个节点")
    if len(nodes) > 120:
        errors.append("节点数量超过 120 个，请拆分图表")
    if len(spec["edges"]) > 240:
        errors.append("关系数量超过 240 条，请拆分图表")

    ids = [node["id"] for node in nodes]
    duplicates = [name for name, count in Counter(ids).items() if count > 1]
    if duplicates:
        errors.append("节点 id 重复: " + ", ".join(duplicates))
    id_set = set(ids)

    for node in nodes:
        if node["type"] not in NODE_TYPES:
            warnings.append(f"节点 {node['id']} 的类型未知，将按 process 渲染")
            node["type"] = "process"
        if spec["kind"] == "sequence" and node["type"] == "participant":
            continue

    for edge in spec["edges"]:
        if not edge["from"] or not edge["to"]:
            errors.append("关系缺少 from 或 to")
        elif edge["from"] not in id_set or edge["to"] not in id_set:
            errors.append(f"关系 {edge['from']} -> {edge['to']} 引用了不存在的节点")
        if edge["type"] not in EDGE_TYPES:
            warnings.append(f"关系类型 {edge['type']} 未知，将按 association 处理")
            edge["type"] = "association"

    for group in spec["groups"]:
        missing = [node_id for node_id in group["nodes"] if node_id not in id_set]
        if missing:
            warnings.append(f"分组 {group['label']} 包含不存在的节点: {', '.join(missing)}")
        group["nodes"] = [node_id for node_id in group["nodes"] if node_id in id_set]

    if spec["kind"] == "sequence":
        orders = [edge["order"] for edge in spec["edges"]]
        if len(orders) != len(set(orders)):
            warnings.append("时序图存在重复 order；将按出现顺序自动排定")
            for index, edge in enumerate(spec["edges"]):
                if orders.count(edge["order"]) > 1:
                    edge["order"] = index + 1

    if spec["kind"] == "class":
        pattern_hint = f"{spec['title']} {spec.get('subtitle', '')}".lower()
        known = (
            "observer", "strategy", "factory", "singleton", "adapter", "decorator",
            "command", "proxy", "builder", "facade", "state", "bridge", "composite",
            "iterator", "mediator", "memento", "visitor", "prototype", "flyweight",
            "interpreter", "responsibility", "template",
            "观察者", "策略", "工厂", "单例", "适配器", "装饰", "命令", "代理",
            "建造", "外观", "状态", "桥接", "组合", "迭代", "中介", "备忘录",
            "访问者", "原型", "享元", "解释器", "职责链", "模板方法",
        )
        if any(word in pattern_hint for word in known):
            stereotypes = " ".join(node["stereotype"].lower() for node in nodes)
            if not any(word in stereotypes for word in ("interface", "abstract", "<<接口>>", "抽象")):
                warnings.append("设计模式图通常应明确接口或抽象角色，可检查是否缺少 <<interface>> / <<abstract>>")

    if spec["kind"] in {"activity", "flow", "state"}:
        if not any(node["type"] in {"start", "end"} for node in nodes):
            warnings.append("流程/状态图建议包含 start 与 end 节点")

    return spec, errors, warnings
