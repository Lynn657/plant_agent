from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from plant_agent.agent import DiagramAgent
from plant_agent.config import AppConfig, APP_ROOT
from plant_agent.mcp import MCPManager
from plant_agent.mermaid import render_mermaid
from plant_agent.render import render_svg
from plant_agent.sessions import SessionStore
from plant_agent.templates import build_offline_diagram
from plant_agent.validation import validate_and_normalize


OFFLINE_CONFIG = AppConfig(
    provider="offline",
    api_key="",
    base_url="",
    model="",
    anthropic_version="2023-06-01",
    max_rounds=8,
    compact_threshold=45000,
    request_timeout=20,
    host="127.0.0.1",
    port=8765,
)


class RendererTests(unittest.TestCase):
    def test_all_diagram_kinds_render(self) -> None:
        kinds = [
            "class",
            "sequence",
            "usecase",
            "activity",
            "state",
            "er",
            "component",
            "deployment",
            "dfd",
            "flow",
        ]
        for kind in kinds:
            with self.subTest(kind=kind):
                spec = build_offline_diagram("在线商城订单系统登录支付审批学生选课图书管理", kind, "ocean")
                normalized, errors, _ = validate_and_normalize(spec)
                self.assertEqual(errors, [])
                svg = render_svg(normalized)
                mermaid = render_mermaid(normalized)
                self.assertIn("<svg", svg)
                self.assertIn("</svg>", svg)
                self.assertGreater(len(svg), 2000)
                self.assertIn("---", mermaid)

    def test_design_pattern_relationships(self) -> None:
        spec = build_offline_diagram("观察者模式类图", "class", "paper")
        edge_types = {edge["type"] for edge in spec["edges"]}
        self.assertIn("realization", edge_types)
        self.assertIn("aggregation", edge_types)
        self.assertIn("Observer", {node["label"] for node in spec["nodes"]})

    def test_invalid_edge_is_reported(self) -> None:
        _, errors, _ = validate_and_normalize(
            {
                "title": "坏图",
                "kind": "class",
                "nodes": [{"id": "A", "label": "A"}],
                "edges": [{"from": "A", "to": "MISSING"}],
            }
        )
        self.assertTrue(any("不存在" in error for error in errors))


class AgentTests(unittest.TestCase):
    def test_offline_agent_and_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = SessionStore(Path(temp))
            session_id = store.new_id()
            agent = DiagramAgent(OFFLINE_CONFIG, session_id)
            try:
                result = agent.generate("画出策略模式类图，并标出 Context 和 Strategy。", "auto", "ocean")
                self.assertIn("策略", result.title)
                self.assertIn("<svg", result.svg)
                self.assertGreater(len(result.todos), 0)
                self.assertTrue(any(item["type"] == "mcp" for item in result.trace))
                store.save(
                    {
                        "id": session_id,
                        "title": result.title,
                        "prompt": result.prompt,
                        "diagram": result.spec,
                        "svg": result.svg,
                        "mermaid": result.mermaid,
                        "trace": result.trace,
                        "todos": result.todos,
                    }
                )
                loaded = store.load(session_id)
                self.assertEqual(loaded["title"], result.title)
                self.assertTrue((Path(temp) / session_id / "diagram.svg").exists())
            finally:
                agent.close()


class MCPTests(unittest.TestCase):
    def test_mcp_handshake_discovery_and_call(self) -> None:
        manager = MCPManager(APP_ROOT / "config" / "mcp_servers.json", APP_ROOT, timeout=10)
        try:
            result = manager.connect("uml-lint")
            self.assertIn("已连接", result)
            self.assertEqual(len(manager.tool_defs()), 2)
            tool_name = next(
                name for name, (_, raw) in manager._tool_map.items() if raw == "validate_spec"
            )
            output = manager.call(
                tool_name,
                {
                    "spec_json": json.dumps(
                        {
                            "title": "MCP 测试",
                            "kind": "class",
                            "nodes": [
                                {"id": "A", "label": "A"},
                                {"id": "B", "label": "B"},
                            ],
                            "edges": [],
                        }
                    )
                },
            )
            data = json.loads(output)
            self.assertTrue(data["ok"])
            self.assertGreaterEqual(len(data["warnings"]), 1)
            self.assertLess(data["score"], 100)
        finally:
            manager.close()


if __name__ == "__main__":
    unittest.main()
