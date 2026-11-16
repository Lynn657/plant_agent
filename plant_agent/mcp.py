from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any


class MCPError(RuntimeError):
    pass


class StdioMCPClient:
    """Minimal MCP stdio client using newline-delimited JSON-RPC."""

    def __init__(
        self,
        name: str,
        command: str,
        args: list[str],
        env: dict[str, str] | None = None,
        timeout: float = 20.0,
        cwd: Path | None = None,
    ):
        self.name = name
        self.command = command
        self.args = args
        self.extra_env = env or {}
        self.timeout = timeout
        self.cwd = cwd
        self.process: subprocess.Popen[str] | None = None
        self.messages: queue.Queue[dict[str, Any]] = queue.Queue()
        self.stderr_lines: list[str] = []
        self._next_id = 1
        self._closed = False
        self.tools: list[dict[str, Any]] = []

    def start(self) -> None:
        env = os.environ.copy()
        env.update(self.extra_env)
        env.setdefault("PYTHONUTF8", "1")
        env.setdefault("PYTHONIOENCODING", "utf-8")
        kwargs: dict[str, Any] = {}
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self.process = subprocess.Popen(
                [self.command, *self.args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                cwd=self.cwd,
                env=env,
                **kwargs,
            )
        except OSError as exc:
            raise MCPError(f"无法启动 MCP server {self.name}: {exc}") from exc
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()
        init_result = self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "plant-agent", "version": "1.0.0"},
            },
            timeout=self.timeout,
        )
        self._notify("notifications/initialized", {})
        tools_result = self._request("tools/list", {}, timeout=self.timeout)
        self.tools = list(tools_result.get("tools") or [])
        if not isinstance(self.tools, list):
            raise MCPError("MCP tools/list 返回格式错误")

    def list_tools(self) -> list[dict[str, Any]]:
        return list(self.tools)

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        result = self._request(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
            timeout=max(self.timeout, 45),
        )
        if result.get("isError"):
            return "MCP tool error: " + _contents_to_text(result.get("content"))
        return _contents_to_text(result.get("content"))

    def stop(self) -> None:
        self._closed = True
        if not self.process:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        for stream_name in ("stdin", "stdout", "stderr"):
            stream = getattr(self.process, stream_name, None)
            if stream:
                try:
                    stream.close()
                except OSError:
                    pass

    def _request(self, method: str, params: dict[str, Any], timeout: float) -> dict[str, Any]:
        if not self.process or not self.process.stdin:
            raise MCPError(f"MCP server {self.name} 未启动")
        request_id = self._next_id
        self._next_id += 1
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        try:
            self.process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            self.process.stdin.flush()
        except OSError as exc:
            raise MCPError(f"写入 MCP 请求失败: {exc}") from exc

        deadline = threading.Event()
        while True:
            try:
                message = self.messages.get(timeout=timeout)
            except queue.Empty as exc:
                raise MCPError(f"MCP server {self.name} 响应超时: {method}") from exc
            if message.get("id") != request_id:
                continue
            if "error" in message:
                error = message["error"]
                raise MCPError(
                    f"MCP {method} 失败: {error.get('message', error)}"
                    if isinstance(error, dict)
                    else f"MCP {method} 失败: {error}"
                )
            result = message.get("result")
            return result if isinstance(result, dict) else {}

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        if not self.process or not self.process.stdin:
            return
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        self.process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def _read_stdout(self) -> None:
        assert self.process and self.process.stdout
        for line in self.process.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self.messages.put(json.loads(line))
            except json.JSONDecodeError:
                self.stderr_lines.append(f"非 JSON 输出: {line[:300]}")
        if not self._closed:
            self.stderr_lines.append("MCP server 已退出")

    def _read_stderr(self) -> None:
        assert self.process and self.process.stderr
        for line in self.process.stderr:
            self.stderr_lines.append(line.rstrip()[:500])
            if len(self.stderr_lines) > 100:
                del self.stderr_lines[:20]


class MCPManager:
    def __init__(self, config_path: Path, app_root: Path, timeout: float = 20.0):
        self.config_path = config_path
        self.app_root = app_root
        self.timeout = timeout
        self.server_configs = self._load_config()
        self.clients: dict[str, StdioMCPClient] = {}
        self._tool_map: dict[str, tuple[str, str]] = {}

    def _load_config(self) -> dict[str, dict[str, Any]]:
        if not self.config_path.exists():
            return {}
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        servers = data.get("mcpServers", {})
        return servers if isinstance(servers, dict) else {}

    def available(self) -> list[dict[str, Any]]:
        result = []
        for name, config in self.server_configs.items():
            result.append(
                {
                    "name": name,
                    "description": str(config.get("description") or ""),
                    "enabled": bool(config.get("enabled", True)),
                    "connected": name in self.clients,
                    "tools": list(self.clients[name].tools) if name in self.clients else [],
                }
            )
        return result

    def connect(self, name: str) -> str:
        if name in self.clients:
            return f"MCP server '{name}' 已连接。"
        config = self.server_configs.get(name)
        if not config:
            return f"未配置 MCP server '{name}'。可用: {', '.join(self.server_configs)}"
        if not config.get("enabled", True):
            return f"MCP server '{name}' 已在配置中禁用。"
        command = self._expand(str(config.get("command") or ""))
        args = [self._expand(str(item)) for item in (config.get("args") or [])]
        env = {
            str(key): self._expand(str(value))
            for key, value in (config.get("env") or {}).items()
        }
        if not command:
            return f"MCP server '{name}' 缺少 command。"
        client = StdioMCPClient(
            name=name,
            command=command,
            args=args,
            env=env,
            timeout=self.timeout,
            cwd=self.app_root,
        )
        try:
            client.start()
        except Exception as exc:
            client.stop()
            return f"MCP 连接失败: {exc}"
        self.clients[name] = client
        self._rebuild_tool_map()
        tools = ", ".join(tool.get("name", "?") for tool in client.tools)
        return f"已连接 MCP server '{name}'，发现 {len(client.tools)} 个工具: {tools or '(无)'}"

    def tool_defs(self) -> list[dict[str, Any]]:
        if not self.clients:
            return []
        self._rebuild_tool_map()
        tools = []
        for prefixed, (server, raw) in self._tool_map.items():
            config = next(
                (tool for tool in self.clients[server].tools if tool.get("name") == raw),
                {},
            )
            tools.append(
                {
                    "name": prefixed,
                    "description": f"[MCP {server}] {config.get('description', '')}",
                    "input_schema": config.get("inputSchema") or {"type": "object", "properties": {}},
                }
            )
        return tools

    def call(self, prefixed_name: str, arguments: dict[str, Any]) -> str:
        target = self._tool_map.get(prefixed_name)
        if not target:
            return f"未知 MCP 工具: {prefixed_name}"
        server, tool = target
        policy = self._policy(server, tool)
        if policy == "deny":
            return f"不允许调用 MCP 工具 {server}/{tool}（宿主策略为 deny）。"
        if policy == "confirm":
            return (
                f"MCP 工具 {server}/{tool} 需要宿主授权。请在 config/mcp_servers.json "
                "中为它配置 \"allow\" 后重试。"
            )
        try:
            return self.clients[server].call_tool(tool, arguments)
        except Exception as exc:
            return f"MCP 调用失败: {exc}"

    def status(self) -> dict[str, Any]:
        return {
            "servers": self.available(),
            "connected": list(self.clients),
            "tools": [
                {"name": name, "server": server, "tool": tool}
                for name, (server, tool) in self._tool_map.items()
            ],
        }

    def close(self) -> None:
        for client in self.clients.values():
            client.stop()
        self.clients.clear()
        self._tool_map.clear()

    def _rebuild_tool_map(self) -> None:
        mapping: dict[str, tuple[str, str]] = {}
        for server_name, client in self.clients.items():
            safe_server = normalize_mcp_name(server_name)
            for raw in client.tools:
                raw_name = str(raw.get("name") or "")
                if not raw_name:
                    continue
                prefixed = f"mcp__{safe_server}__{normalize_mcp_name(raw_name)}"
                if len(prefixed) > 64:
                    prefixed = prefixed[:64]
                mapping[prefixed] = (server_name, raw_name)
        self._tool_map = mapping

    def _policy(self, server: str, tool: str) -> str:
        config = self.server_configs.get(server, {})
        policy = config.get("policy") or {}
        value = policy.get(tool, policy.get("*", "confirm"))
        return str(value).lower() if str(value).lower() in {"allow", "confirm", "deny"} else "confirm"

    def _expand(self, value: str) -> str:
        return (
            value.replace("${PYTHON}", sys.executable)
            .replace("${APP_ROOT}", str(self.app_root))
        )


def normalize_mcp_name(name: str) -> str:
    result = re.sub(r"[^A-Za-z0-9_]", "_", name)
    return re.sub(r"_+", "_", result).strip("_") or "tool"


def _contents_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)
    if not isinstance(content, list):
        return str(content or "")
    chunks = []
    for item in content:
        if isinstance(item, dict):
            if item.get("type") == "text":
                chunks.append(str(item.get("text") or ""))
            else:
                chunks.append(json.dumps(item, ensure_ascii=False))
        else:
            chunks.append(str(item))
    return "\n".join(chunks)
