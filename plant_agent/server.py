from __future__ import annotations

import json
import mimetypes
import threading
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .agent import DiagramAgent
from .config import WEB_DIR, ensure_directories, get_config
from .mcp import MCPManager
from .mermaid import render_mermaid
from .render import render_svg
from .sessions import SessionStore
from .skills import SkillRegistry
from .validation import validate_and_normalize


class PlantAgentHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int]):
        super().__init__(address, PlantAgentHandler)
        self.config = get_config()
        ensure_directories()
        self.sessions = SessionStore(Path(__file__).resolve().parent.parent / "data" / "sessions")
        self.skills = SkillRegistry(Path(__file__).resolve().parent.parent / "skills")
        self.mcp = MCPManager(
            Path(__file__).resolve().parent.parent / "config" / "mcp_servers.json",
            Path(__file__).resolve().parent.parent,
        )


class PlantAgentHandler(BaseHTTPRequestHandler):
    server: PlantAgentHTTPServer
    server_version = "PlantAgent/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[http] {self.address_string()} {format % args}")

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/status":
            self._json(
                {
                    **self.server.config.public_status,
                    "skills": self.server.skills.public_catalog(),
                    "mcp": self.server.mcp.status(),
                    "sessions": self.server.sessions.list(12),
                }
            )
            return
        if parsed.path == "/api/sessions":
            self._json({"sessions": self.server.sessions.list(40)})
            return
        if parsed.path == "/api/session":
            session_id = urllib.parse.parse_qs(parsed.query).get("id", [""])[0]
            try:
                session = self.server.sessions.load(session_id)
            except ValueError as exc:
                self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            if not session:
                self._json({"error": "会话不存在"}, HTTPStatus.NOT_FOUND)
                return
            self._json(session)
            return
        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        try:
            body = self._read_json()
        except ValueError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/generate":
            self._generate(body)
            return
        if parsed.path == "/api/render":
            self._render_direct(body)
            return
        if parsed.path == "/api/mcp/connect":
            name = str(body.get("name") or "")
            result = self.server.mcp.connect(name)
            self._json({"result": result, "mcp": self.server.mcp.status()})
            return
        self._json({"error": "接口不存在"}, HTTPStatus.NOT_FOUND)

    def _generate(self, body: dict[str, Any]) -> None:
        prompt = str(body.get("prompt") or "").strip()
        if not prompt:
            self._json({"error": "请输入题目信息"}, HTTPStatus.BAD_REQUEST)
            return
        if len(prompt) > 20000:
            self._json({"error": "题目信息过长（最多 20,000 字符）"}, HTTPStatus.BAD_REQUEST)
            return
        requested_id = str(body.get("session_id") or "").strip()
        previous = None
        if requested_id:
            try:
                previous = self.server.sessions.load(requested_id)
            except ValueError:
                previous = None
        session_id = previous["id"] if previous else self.server.sessions.new_id()
        session_context = ""
        if previous:
            session_context = (
                f"上一轮题目: {previous.get('prompt', '')[:2000]}\n"
                f"上一轮摘要: {previous.get('summary', '')[:2000]}\n"
                f"上一版规格: {json.dumps(previous.get('diagram', {}), ensure_ascii=False)[:4000]}"
            )
        agent = DiagramAgent(self.server.config, session_id)
        try:
            result = agent.generate(
                prompt=prompt,
                requested_kind=str(body.get("kind") or "auto"),
                theme=str(body.get("theme") or "ocean"),
                session_context=session_context,
            )
            data = result.as_dict()
            session = {
                "id": session_id,
                "title": result.title,
                "prompt": prompt,
                "created_at": (previous or {}).get("created_at", ""),
                "updated_at": "",
                "summary": result.summary,
                "diagram": result.spec,
                "svg": result.svg,
                "mermaid": result.mermaid,
                "trace": result.trace,
                "todos": result.todos,
                "warnings": result.warnings,
                "kind": result.spec["kind"],
                "theme": body.get("theme") or "ocean",
            }
            self.server.sessions.save(session)
            self.server.sessions.append_transcript(
                session_id,
                {"prompt": prompt, "result": {**data, "svg": "<omitted>"}},
            )
            self._json(data)
        except Exception as exc:
            self._json(
                {
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "session_id": session_id,
                },
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
        finally:
            agent.close()

    def _render_direct(self, body: dict[str, Any]) -> None:
        spec, errors, warnings = validate_and_normalize(body.get("spec") or body)
        if errors:
            self._json({"error": "规格错误", "details": errors}, HTTPStatus.BAD_REQUEST)
            return
        spec["theme"] = str(body.get("theme") or spec.get("theme") or "ocean")
        self._json(
            {
                "diagram": spec,
                "svg": render_svg(spec),
                "mermaid": render_mermaid(spec),
                "warnings": warnings,
            }
        )

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("无效的 Content-Length") from exc
        if length <= 0:
            return {}
        if length > 2_000_000:
            raise ValueError("请求体过大")
        raw = self.rfile.read(length)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("请求体不是有效 JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("请求体必须是 JSON 对象")
        return value

    def _serve_static(self, url_path: str) -> None:
        relative = "index.html" if url_path in {"", "/"} else url_path.lstrip("/")
        target = (WEB_DIR / relative).resolve()
        if not target.is_relative_to(WEB_DIR.resolve()) or not target.is_file():
            self._json({"error": "文件不存在"}, HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if target.suffix in {".html", ".css", ".js", ".svg", ".json"}:
            content_type += "; charset=utf-8"
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def run_server(host: str | None = None, port: int | None = None, open_browser: bool = True) -> None:
    config = get_config()
    host = host or config.host
    port = port or config.port
    server = PlantAgentHTTPServer((host, port))
    actual_port = server.server_address[1]
    url = f"http://{host}:{actual_port}"
    print("=" * 64)
    print("PlantAgent · 软件工程与设计模式绘图代理")
    print(f"工作台: {url}")
    print(f"模型: {config.model if config.llm_ready else '离线模板模式'}")
    print("按 Ctrl+C 停止服务")
    print("=" * 64)
    if open_browser:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n正在关闭 PlantAgent...")
    finally:
        server.mcp.close()
        server.server_close()
