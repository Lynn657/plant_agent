from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from plant_agent.config import get_config
from plant_agent.sessions import SessionStore
from plant_agent.server import run_server


def main() -> int:
    parser = argparse.ArgumentParser(description="PlantAgent - 软件工程与设计模式绘图代理")
    parser.add_argument("--host", help="监听地址，默认 127.0.0.1")
    parser.add_argument("--port", type=int, help="监听端口，默认 8765")
    parser.add_argument("--no-browser", action="store_true", help="启动时不打开浏览器")
    parser.add_argument("--demo", metavar="TOPIC", help="离线生成一个示例到 data/sessions 后退出")
    parser.add_argument("--kind", default="auto", help="示例图类型")
    args = parser.parse_args()
    if args.demo:
        from plant_agent.agent import DiagramAgent

        store = SessionStore(Path(__file__).resolve().parent / "data" / "sessions")
        session_id = store.new_id()
        agent = DiagramAgent(get_config(), session_id)
        try:
            result = agent.generate(args.demo, args.kind)
            store.save(
                {
                    "id": session_id,
                    "title": result.title,
                    "prompt": result.prompt,
                    "created_at": "",
                    "summary": result.summary,
                    "diagram": result.spec,
                    "svg": result.svg,
                    "mermaid": result.mermaid,
                    "trace": result.trace,
                    "todos": result.todos,
                    "warnings": result.warnings,
                    "kind": result.spec["kind"],
                }
            )
            print(json.dumps({"session_id": session_id, "title": result.title}, ensure_ascii=False))
        finally:
            agent.close()
        return 0
    run_server(args.host, args.port, not args.no_browser)
    return 0


if __name__ == "__main__":
    sys.exit(main())
