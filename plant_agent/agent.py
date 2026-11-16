from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

from .collaboration import BackgroundJobs, ReviewTeam
from .config import AppConfig, CONFIG_DIR, APP_ROOT
from .mcp import MCPManager
from .mermaid import render_mermaid
from .models import DIAGRAM_KINDS
from .providers import LLMError, ToolCall, create_provider
from .render import render_svg
from .skills import SkillRegistry
from .state import MemoryStore, TodoManager
from .templates import build_offline_diagram
from .validation import validate_and_normalize


def _tool(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required or [],
        },
    }


TOOLS: list[dict[str, Any]] = [
    _tool(
        "load_skill",
        "按需加载软件工程、设计模式或绘图质量知识。",
        {"name": {"type": "string", "description": "技能名"}},
        ["name"],
    ),
    _tool(
        "set_plan",
        "建立或更新当前绘图步骤。仅一个步骤可处于 in_progress。",
        {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "text": {"type": "string"},
                        "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                    },
                    "required": ["id", "text", "status"],
                },
            }
        },
        ["items"],
    ),
    _tool(
        "create_diagram",
        (
            "验证并渲染最终图表。spec_json 必须是完整 JSON 字符串或对象。"
            "会生成 SVG 与 Mermaid，并保存为当前会话的图表版本。"
        ),
        {
            "spec_json": {"type": "string", "description": "DiagramSpec JSON"},
            "explanation": {"type": "string", "description": "一句话说明建模决策"},
        },
        ["spec_json"],
    ),
    _tool(
        "inspect_diagram",
        "检查当前或指定图表的结构、孤立节点、关系语义和布局风险。",
        {
            "spec_json": {"type": "string", "description": "可选；留空检查当前图"},
            "focus": {"type": "string", "description": "可选检查重点"},
        },
    ),
    _tool(
        "delegate_review",
        "启动一个无历史上下文的评审子代理，对本图做领域建模和可读性复核。",
        {
            "spec_json": {"type": "string", "description": "可选；留空评审当前图"},
            "focus": {"type": "string", "description": "评审重点"},
        },
    ),
    _tool(
        "review_panel",
        "启动 UML 与需求两个独立评审员并行复核复杂图表。比单次自检更严格。",
        {
            "focus": {"type": "string", "description": "评审重点"},
        },
    ),
    _tool(
        "remember",
        "记住用户偏好或长期建模约定。",
        {
            "key": {"type": "string"},
            "value": {"type": "string"},
        },
        ["key", "value"],
    ),
    _tool(
        "recall",
        "读取长期记忆；key 留空时返回全部。",
        {"key": {"type": "string"}},
    ),
    _tool(
        "list_mcp_servers",
        "列出配置中的 MCP server、连接状态和已发现工具。",
        {},
    ),
    _tool(
        "connect_mcp",
        "连接配置中的 MCP server；成功后下一轮会看到 mcp__server__tool 形式的工具。",
        {"name": {"type": "string"}},
        ["name"],
    ),
]


@dataclass(slots=True)
class AgentResult:
    session_id: str
    title: str
    prompt: str
    spec: dict[str, Any]
    svg: str
    mermaid: str
    summary: str
    trace: list[dict[str, str]]
    todos: list[dict[str, str]]
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "prompt": self.prompt,
            "diagram": self.spec,
            "svg": self.svg,
            "mermaid": self.mermaid,
            "summary": self.summary,
            "trace": self.trace,
            "todos": self.todos,
            "warnings": self.warnings,
        }


class DiagramAgent:
    def __init__(self, config: AppConfig, session_id: str):
        self.config = config
        self.session_id = session_id
        self.skills = SkillRegistry(APP_ROOT / "skills")
        self.memory = MemoryStore(APP_ROOT / "data" / "memory.json")
        self.todos = TodoManager()
        self.mcp = MCPManager(
            CONFIG_DIR / "mcp_servers.json",
            APP_ROOT,
            timeout=min(30, config.request_timeout),
        )
        self.provider = create_provider(config)
        self.background = BackgroundJobs(2)
        self.review_team = ReviewTeam(self.provider) if self.provider else None
        self.messages: list[dict[str, Any]] = []
        self.trace: list[dict[str, str]] = []
        self.latest_spec: dict[str, Any] | None = None
        self.latest_svg = ""
        self.latest_mermaid = ""
        self.warnings: list[str] = []
        self.prompt = ""
        self.diagram_explanation = ""

    def generate(
        self,
        prompt: str,
        requested_kind: str = "auto",
        theme: str = "ocean",
        session_context: str = "",
    ) -> AgentResult:
        self.prompt = prompt.strip()
        if not self.prompt:
            raise ValueError("题目信息不能为空")
        requested_kind = requested_kind if requested_kind in DIAGRAM_KINDS else "auto"
        if theme not in {"ocean", "paper", "dark"}:
            theme = "ocean"
        self._trace("model", f"模型：{self.config.model if self.config.llm_ready else '离线模板'}", "")

        if not self.config.llm_ready or self.provider is None:
            self._run_offline(requested_kind, theme)
        else:
            try:
                self._run_llm(prompt, requested_kind, theme, session_context)
            except Exception as exc:
                self.warnings.append(f"模型代理执行失败，已切换离线模板：{exc}")
                self._trace("warning", "模型代理失败，切换离线模板", str(exc))
                self._run_offline(requested_kind, theme, preserve_trace=True)

        if not self.latest_spec:
            raise RuntimeError("代理未生成有效图表")
        final_summary = next(
            (
                str(message.get("content"))
                for message in reversed(self.messages)
                if message.get("role") == "assistant" and message.get("content")
            ),
            "",
        )
        if not final_summary:
            final_summary = (
                f"已生成《{self.latest_spec['title']}》。"
                + ("这是离线模板结果；配置模型后可围绕题目信息自由建模。" if not self.config.llm_ready else "")
            )
        self._trace("done", "图表已保存", self.latest_spec["title"])
        return AgentResult(
            session_id=self.session_id,
            title=self.latest_spec["title"],
            prompt=self.prompt,
            spec=self.latest_spec,
            svg=self.latest_svg,
            mermaid=self.latest_mermaid,
            summary=final_summary,
            trace=self.trace,
            todos=list(self.todos.items),
            warnings=self.warnings,
        )

    def _run_offline(
        self,
        requested_kind: str,
        theme: str,
        preserve_trace: bool = False,
    ) -> None:
        if not preserve_trace:
            self._trace("plan", "建立离线建模步骤", "")
        self._apply_plan(
            [
                {"id": "1", "text": "识别图表类型与建模意图", "status": "completed"},
                {"id": "2", "text": "按需加载领域知识", "status": "in_progress"},
                {"id": "3", "text": "构建并渲染图表", "status": "pending"},
                {"id": "4", "text": "执行结构校验", "status": "pending"},
            ]
        )
        skill_name = "design-patterns" if requested_kind in {"auto", "class"} else "software-engineering"
        loaded = self.skills.load(skill_name)
        self._trace("skill", f"加载技能 {skill_name}", loaded[:160])
        spec = build_offline_diagram(self.prompt, requested_kind, theme)
        self._apply_plan(
            [
                {"id": "1", "text": "识别图表类型与建模意图", "status": "completed"},
                {"id": "2", "text": "按需加载领域知识", "status": "completed"},
                {"id": "3", "text": "构建并渲染图表", "status": "in_progress"},
                {"id": "4", "text": "执行结构校验", "status": "pending"},
            ]
        )
        self._create_diagram(spec, "离线模板依据题目关键词生成结构，并统一应用当前主题。")
        self._apply_plan(
            [
                {"id": "1", "text": "识别图表类型与建模意图", "status": "completed"},
                {"id": "2", "text": "按需加载领域知识", "status": "completed"},
                {"id": "3", "text": "构建并渲染图表", "status": "completed"},
                {"id": "4", "text": "执行结构校验", "status": "in_progress"},
            ]
        )
        inspection = self._inspect(None, "检查角色完整性、孤立节点与关系方向")
        self._trace("tool", "结构校验", inspection[:500])
        if "uml-lint" in self.mcp.server_configs:
            connect = self.mcp.connect("uml-lint")
            self._trace("mcp", "连接 MCP 校验工具", connect)
            for prefixed, (server, tool) in self.mcp._tool_map.items():
                if server == "uml-lint" and tool == "validate_spec":
                    result = self.mcp.call(prefixed, {"spec_json": json.dumps(self.latest_spec, ensure_ascii=False)})
                    self._trace("mcp", "MCP 二次校验", result[:500])
                    self.warnings.extend(_extract_mcp_warnings(result))
                    break
        self._apply_plan(
            [
                {"id": "1", "text": "识别图表类型与建模意图", "status": "completed"},
                {"id": "2", "text": "按需加载领域知识", "status": "completed"},
                {"id": "3", "text": "构建并渲染图表", "status": "completed"},
                {"id": "4", "text": "执行结构校验", "status": "completed"},
            ]
        )
        if not self.config.llm_ready:
            self.messages.append(
                {
                    "role": "assistant",
                    "content": (
                        f"已生成《{self.latest_spec['title']}》。当前为离线模板模式："
                        "常见设计模式与软件工程图可直接使用；复杂或高度定制题目建议在 .env 配置模型。"
                    ),
                }
            )

    def _run_llm(
        self,
        prompt: str,
        requested_kind: str,
        theme: str,
        session_context: str,
    ) -> None:
        context = ""
        if session_context:
            context = f"\n<previous-session>\n{session_context[:6000]}\n</previous-session>\n"
        self.messages.append(
            {
                "role": "user",
                "content": (
                    f"{context}<task>\n{prompt}\n</task>\n"
                    f"优先图类型: {requested_kind}\n主题: {theme}\n"
                    "请完成建模、生成并自检。不要只解释，必须调用 create_diagram。"
                ),
            }
        )
        rounds = 0
        for _ in range(self.config.max_rounds):
            rounds += 1
            self._compact_if_needed()
            tools = TOOLS + self.mcp.tool_defs()
            response = self.provider.complete(self._system_prompt(), self.messages, tools)
            if response.text:
                self._trace("model", "模型输出", response.text[:500])
            self.messages.append(
                {
                    "role": "assistant",
                    "content": response.text,
                    "tool_calls": [
                        {"id": call.id, "name": call.name, "arguments": call.arguments}
                        for call in response.tool_calls
                    ],
                }
            )
            if not response.tool_calls:
                break
            for call in response.tool_calls:
                result = self._execute_tool(call)
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.name,
                        "content": result[:50000],
                    }
                )
        else:
            self.warnings.append(f"达到最大代理轮数 {self.config.max_rounds}，停止继续调用工具。")
        if not self.latest_spec:
            raise RuntimeError("模型结束前没有调用 create_diagram，无法产出图表")

    def _execute_tool(self, call: ToolCall) -> str:
        name = call.name
        args = call.arguments
        self._trace("tool", f"调用 {name}", _short_args(args))
        try:
            if name == "load_skill":
                return self.skills.load(str(args.get("name") or ""))
            if name == "set_plan":
                return self._apply_plan(args.get("items") or [])
            if name == "create_diagram":
                return self._create_diagram(args.get("spec_json"), args.get("explanation", ""))
            if name == "inspect_diagram":
                return self._inspect(args.get("spec_json"), args.get("focus", ""))
            if name == "delegate_review":
                return self._delegate_review(args.get("spec_json"), args.get("focus", ""))
            if name == "review_panel":
                return self._review_panel(args.get("focus", ""))
            if name == "remember":
                return self.memory.remember(str(args.get("key") or ""), str(args.get("value") or ""))
            if name == "recall":
                return self.memory.recall(str(args.get("key") or ""))
            if name == "list_mcp_servers":
                return json.dumps(self.mcp.status(), ensure_ascii=False, indent=2)
            if name == "connect_mcp":
                result = self.mcp.connect(str(args.get("name") or ""))
                self._trace("mcp", "MCP 连接", result)
                return result
            if name.startswith("mcp__"):
                result = self.mcp.call(name, args)
                self._trace("mcp", f"调用 {name}", result[:300])
                return result
            return f"未知工具: {name}"
        except Exception as exc:
            return f"工具错误 {name}: {type(exc).__name__}: {exc}"

    def _create_diagram(self, spec_input: Any, explanation: str = "") -> str:
        raw = _parse_json_value(spec_input)
        spec, errors, warnings = validate_and_normalize(raw)
        if errors:
            return "图表规格有错误，请修正后重试:\n" + "\n".join(f"- {error}" for error in errors)
        jobs = [
            self.background.submit("svg", render_svg, spec),
            self.background.submit("mermaid", render_mermaid, spec),
        ]
        rendered = self.background.collect(jobs)
        if isinstance(rendered.get("svg"), Exception):
            raise rendered["svg"]
        if isinstance(rendered.get("mermaid"), Exception):
            raise rendered["mermaid"]
        svg = rendered["svg"]
        mermaid = rendered["mermaid"]
        self.latest_spec = spec
        self.latest_svg = svg
        self.latest_mermaid = mermaid
        self.diagram_explanation = str(explanation or "")[:500]
        self.warnings.extend(item for item in warnings if item not in self.warnings)
        self._trace(
            "diagram",
            f"已渲染《{spec['title']}》",
            f"{len(spec['nodes'])} 个节点，{len(spec['edges'])} 条关系；{self.diagram_explanation}",
        )
        return json.dumps(
            {
                "ok": True,
                "title": spec["title"],
                "kind": spec["kind"],
                "nodes": len(spec["nodes"]),
                "edges": len(spec["edges"]),
                "warnings": warnings,
                "svg_bytes": len(svg.encode("utf-8")),
            },
            ensure_ascii=False,
        )

    def _inspect(self, spec_input: Any, focus: str = "") -> str:
        if spec_input:
            spec, errors, warnings = validate_and_normalize(_parse_json_value(spec_input))
        elif self.latest_spec:
            spec, errors, warnings = validate_and_normalize(self.latest_spec)
        else:
            return "当前没有可检查的图表。"
        node_ids = {node["id"] for node in spec["nodes"]}
        connected = set()
        for edge in spec["edges"]:
            connected.add(edge["from"])
            connected.add(edge["to"])
        isolated = sorted(node_ids - connected)
        if len(spec["nodes"]) > 1 and isolated:
            warnings.append("孤立节点: " + ", ".join(isolated))
        if spec["kind"] == "class" and spec["nodes"]:
            unnamed = [node["id"] for node in spec["nodes"] if not node["label"].strip()]
            if unnamed:
                errors.append("类图存在未命名节点: " + ", ".join(unnamed))
        if spec["kind"] == "sequence":
            if any(edge["type"] not in {"sync", "async", "return", "flow"} for edge in spec["edges"]):
                warnings.append("时序图中存在非消息型关系，建议使用 sync/async/return")
        return json.dumps(
            {
                "focus": focus or "结构完整性",
                "ok": not errors,
                "errors": errors,
                "warnings": warnings,
                "stats": {
                    "nodes": len(spec["nodes"]),
                    "edges": len(spec["edges"]),
                    "groups": len(spec["groups"]),
                    "isolated": isolated,
                },
                "summary": "结构完整，可以交付。" if not errors else "需要修正结构化错误。",
            },
            ensure_ascii=False,
            indent=2,
        )

    def _delegate_review(self, spec_input: Any, focus: str = "") -> str:
        if not self.latest_spec and not spec_input:
            return "当前没有可供评审的图表。"
        spec = _parse_json_value(spec_input) if spec_input else self.latest_spec
        review = (
            "你是一名独立软件架构评审员。只返回可执行的建模问题，不重复描述图表。"
            "重点检查：角色职责、关系方向、UML 语义、题目信息是否遗漏、图中是否存在歧义。"
            f"评审重点：{focus or '整体质量'}"
        )
        if not self.provider or not self.config.llm_ready:
            return self._inspect(json.dumps(spec, ensure_ascii=False), focus)
        messages = [
            {
                "role": "user",
                "content": review + "\n\n<diagram>\n" + json.dumps(spec, ensure_ascii=False)[:30000] + "\n</diagram>",
            }
        ]
        response = self.provider.complete(
            "你是严格但务实的 UML 与软件架构评审子代理。",
            messages,
            [],
        )
        self._trace("subagent", "评审子代理返回结果", response.text[:500])
        return response.text or "子代理未返回评审意见。"

    def _review_panel(self, focus: str = "") -> str:
        if not self.latest_spec:
            return "当前没有可供评审的图表。"
        if not self.review_team or not self.config.llm_ready:
            return self._inspect(None, focus)
        output = self.review_team.review(self.latest_spec, focus)
        self._trace("team", "双角色评审完成", output[:800])
        return output

    def _apply_plan(self, items: list[dict[str, Any]]) -> str:
        in_progress = [item for item in items if str(item.get("status")) == "in_progress"]
        if len(in_progress) > 1:
            raise ValueError("同一时间只能有一个 in_progress 待办")
        result = self.todos.update(items)
        self._trace("plan", "更新任务计划", result.replace("\n", " · "))
        return result

    def _system_prompt(self) -> str:
        memory = self.memory.summary()
        mcp_servers = ", ".join(
            f"{item['name']}({'已连接' if item['connected'] else '可连接'})"
            for item in self.mcp.available()
        ) or "无"
        schema = (
            '{"title":"标题","subtitle":"副标题","kind":"class|sequence|usecase|activity|state|er|component|deployment|flow|dfd",'
            '"theme":"ocean|paper|dark","direction":"LR|TB","nodes":[{"id":"唯一id","label":"名称",'
            '"type":"class|interface|abstract|actor|usecase|process|decision|entity|database|component|service|node|state|start|end|participant|external|datastore",'
            '"stereotype":"<<interface>>","attributes":["属性"],"methods":["方法"]}],'
            '"edges":[{"from":"id","to":"id","type":"association|inheritance|realization|composition|aggregation|dependency|flow|sync|async|return|include|extend|data",'
            '"label":"关系","number":"1","order":1,"guard":"条件"}],'
            '"groups":[{"id":"边界id","label":"系统边界","nodes":["id"]}],"notes":["假设/说明"],"legend":true}'
        )
        return f"""你是 PlantAgent，一名同时精通 UML、软件工程和 GoF 设计模式的绘图代理。

工作流程：
1. 先用 set_plan 建立 3-5 个步骤。
2. 按需 load_skill，不要一次加载所有知识。
3. 从用户题目中抽取参与者、对象、状态、消息、数据或模式角色；不要臆造与该题无关的大系统。
4. 构建 DiagramSpec，调用 create_diagram。规格错误时读取错误并修正。
5. 调用 inspect_diagram。复杂类图/设计模式可调用 delegate_review。
6. 只有图已成功渲染才结束；最终中文回复只概述建模决策和必要假设。

DiagramSpec:
{schema}

建模规则：
- 类图使用 interface/abstract/class，设计模式边要区分 inheritance、realization、composition、aggregation、dependency。
- 时序图节点使用 participant（人类参与者用 actor），edges.order 从 1 递增，返回消息用 return。
- 用例图将 actor 放在系统边界外，usecase 放入 groups，公共用例可用 include。
- 状态与活动图应有 start/end；判断节点用 decision，迁移用 flow。
- ER 图 entity 的 attributes 写主键/外键，关系 label 带 1:N 等基数。
- 节点通常控制在 5-18 个；超过 18 个应拆分或简化。
- 明确区分事实与假设，假设写进 notes。

可用技能：
{self.skills.catalog()}

MCP servers: {mcp_servers}
如题目确实需要外部能力，可 connect_mcp；已连接工具以 mcp__server__tool 出现。
长期记忆：{memory or "无"}
"""

    def _compact_if_needed(self) -> None:
        if _estimate_tokens(self.messages) <= self.config.compact_threshold:
            self._micro_compact()
            return
        spec_summary = json.dumps(self.latest_spec or {}, ensure_ascii=False)[:5000]
        plan = self.todos.render()
        summary = (
            "上一段上下文已压缩。保留当前图表规格、计划与建模目标。\n"
            f"用户目标：{self.prompt[:1000]}\n当前计划：{plan}\n当前规格：{spec_summary}"
        )
        self.messages = [{"role": "user", "content": summary}]
        self._trace("memory", "上下文已压缩", f"保留 {len(summary)} 字符关键状态")

    def _micro_compact(self) -> None:
        tool_indexes = [index for index, message in enumerate(self.messages) if message.get("role") == "tool"]
        for index in tool_indexes[:-4]:
            message = self.messages[index]
            if len(str(message.get("content") or "")) > 1500:
                message["content"] = f"[较早的 {message.get('name', '工具')} 结果已压缩]"

    def _trace(self, kind: str, title: str, detail: str) -> None:
        self.trace.append(
            {
                "time": time.strftime("%H:%M:%S"),
                "type": kind,
                "title": title[:160],
                "detail": str(detail)[:1200],
            }
        )

    def close(self) -> None:
        self.background.close()
        self.mcp.close()


def _parse_json_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    text = str(value or "").strip()
    if not text:
        raise ValueError("JSON 内容为空")
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 格式错误: {exc}") from exc


def _estimate_tokens(messages: list[dict[str, Any]]) -> int:
    return len(str(messages)) // 4


def _short_args(args: dict[str, Any]) -> str:
    clean = {}
    for key, value in args.items():
        if key in {"spec_json", "content"}:
            clean[key] = f"<{len(str(value))} chars>"
        else:
            clean[key] = str(value)[:180]
    return json.dumps(clean, ensure_ascii=False)


def _extract_mcp_warnings(result: str) -> list[str]:
    try:
        data = json.loads(result)
    except json.JSONDecodeError:
        return []
    warnings = data.get("warnings") if isinstance(data, dict) else []
    return [str(item)[:300] for item in warnings[:10]] if isinstance(warnings, list) else []
