from __future__ import annotations

import json
import threading
import unittest
import urllib.request

from plant_agent.server import PlantAgentHTTPServer


class ServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = PlantAgentHTTPServer(("127.0.0.1", 0))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.mcp.close()
        self.server.server_close()
        self.thread.join(timeout=3)

    def test_status_and_direct_render(self) -> None:
        with urllib.request.urlopen(self.base + "/api/status", timeout=5) as response:
            status = json.loads(response.read())
        self.assertIn("skills", status)
        self.assertGreaterEqual(len(status["skills"]), 3)

        payload = json.dumps(
            {
                "title": "API 绘图测试",
                "kind": "sequence",
                "theme": "dark",
                "nodes": [
                    {"id": "A", "label": "用户", "type": "actor"},
                    {"id": "B", "label": "服务", "type": "participant"},
                ],
                "edges": [{"from": "A", "to": "B", "label": "请求", "type": "sync"}],
            }
        ).encode()
        request = urllib.request.Request(
            self.base + "/api/render",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            data = json.loads(response.read())
        self.assertIn("<svg", data["svg"])
        self.assertIn("sequenceDiagram", data["mermaid"])


if __name__ == "__main__":
    unittest.main()
