from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from .config import AppConfig


@dataclass(slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class LLMResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMError(RuntimeError):
    pass


class OpenAICompatibleProvider:
    def __init__(self, config: AppConfig):
        self.config = config

    def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        oa_messages = [{"role": "system", "content": system}]
        for message in messages:
            role = message.get("role")
            if role == "assistant":
                item: dict[str, Any] = {"role": "assistant", "content": message.get("content") or ""}
                calls = message.get("tool_calls") or []
                if calls:
                    item["tool_calls"] = [
                        {
                            "id": call["id"],
                            "type": "function",
                            "function": {
                                "name": call["name"],
                                "arguments": json.dumps(call.get("arguments") or {}, ensure_ascii=False),
                            },
                        }
                        for call in calls
                    ]
                oa_messages.append(item)
            elif role == "tool":
                oa_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": message.get("tool_call_id", ""),
                        "content": str(message.get("content") or ""),
                    }
                )
            else:
                oa_messages.append({"role": "user", "content": str(message.get("content") or "")})

        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": oa_messages,
            "temperature": 0.2,
            "max_tokens": 6000,
        }
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema") or {"type": "object", "properties": {}},
                    },
                }
                for tool in tools
            ]
            payload["tool_choice"] = "auto"
        base = self.config.base_url.rstrip("/")
        url = base if base.endswith("/chat/completions") else base + "/chat/completions"
        data = _post_json(
            url,
            payload,
            {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            self.config.request_timeout,
        )
        choices = data.get("choices") or []
        if not choices:
            raise LLMError("模型响应中没有 choices")
        message = choices[0].get("message") or {}
        text = _openai_text(message.get("content"))
        calls = []
        for item in message.get("tool_calls") or []:
            function = item.get("function") or {}
            arguments = function.get("arguments") or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError as exc:
                    raise LLMError(f"模型生成了无效的工具参数 JSON: {exc}") from exc
            calls.append(
                ToolCall(
                    id=str(item.get("id") or f"call_{len(calls) + 1}"),
                    name=str(function.get("name") or ""),
                    arguments=arguments if isinstance(arguments, dict) else {"value": arguments},
                )
            )
        return LLMResponse(text=text, tool_calls=calls)


class AnthropicProvider:
    def __init__(self, config: AppConfig):
        self.config = config

    def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "system": system,
            "messages": _to_anthropic_messages(messages),
            "max_tokens": 6000,
            "temperature": 0.2,
        }
        if tools:
            payload["tools"] = [
                {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("input_schema") or {"type": "object", "properties": {}},
                }
                for tool in tools
            ]
        base = self.config.base_url.rstrip("/")
        url = base + "/v1/messages" if not base.endswith("/v1/messages") else base
        data = _post_json(
            url,
            payload,
            {
                "x-api-key": self.config.api_key,
                "anthropic-version": self.config.anthropic_version,
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            self.config.request_timeout,
        )
        text_parts = []
        calls = []
        for block in data.get("content") or []:
            block_type = block.get("type")
            if block_type == "text":
                text_parts.append(str(block.get("text") or ""))
            elif block_type == "tool_use":
                calls.append(
                    ToolCall(
                        id=str(block.get("id") or f"tool_{len(calls) + 1}"),
                        name=str(block.get("name") or ""),
                        arguments=block.get("input") if isinstance(block.get("input"), dict) else {},
                    )
                )
        return LLMResponse(text="\n".join(part for part in text_parts if part), tool_calls=calls)


def create_provider(config: AppConfig):
    if config.provider == "anthropic":
        return AnthropicProvider(config)
    if config.provider == "openai":
        return OpenAICompatibleProvider(config)
    return None


def _post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        detail = _error_detail(body)
        raise LLMError(f"模型接口 HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise LLMError(f"无法连接模型接口: {exc.reason}") from exc
    except TimeoutError as exc:
        raise LLMError("模型请求超时") from exc
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise LLMError(f"模型接口返回了非 JSON 内容: {body[:400]}") from exc
    if not isinstance(data, dict):
        raise LLMError("模型接口返回格式错误")
    return data


def _error_detail(body: str) -> str:
    try:
        data = json.loads(body)
        if isinstance(data, dict):
            error = data.get("error", data)
            if isinstance(error, dict):
                return str(error.get("message") or error)[:500]
            return str(error)[:500]
    except json.JSONDecodeError:
        pass
    return body[:500]


def _to_anthropic_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for message in messages:
        role = message.get("role")
        if role == "assistant":
            content = []
            if message.get("content"):
                content.append({"type": "text", "text": str(message["content"])})
            for call in message.get("tool_calls") or []:
                content.append(
                    {
                        "type": "tool_use",
                        "id": call["id"],
                        "name": call["name"],
                        "input": call.get("arguments") or {},
                    }
                )
            converted.append({"role": "assistant", "content": content or [{"type": "text", "text": "..."}]})
        elif role == "tool":
            block = {
                "type": "tool_result",
                "tool_use_id": message.get("tool_call_id", ""),
                "content": str(message.get("content") or ""),
            }
            if converted and converted[-1]["role"] == "user" and isinstance(converted[-1]["content"], list):
                converted[-1]["content"].append(block)
            else:
                converted.append({"role": "user", "content": [block]})
        else:
            converted.append({"role": "user", "content": str(message.get("content") or "")})

    # Anthropic permits only alternating user/assistant roles. Tool results may
    # create adjacent user messages, so merge text blocks while preserving order.
    merged: list[dict[str, Any]] = []
    for message in converted:
        if merged and merged[-1]["role"] == message["role"]:
            left = merged[-1]["content"]
            right = message["content"]
            left_blocks = left if isinstance(left, list) else [{"type": "text", "text": str(left)}]
            right_blocks = right if isinstance(right, list) else [{"type": "text", "text": str(right)}]
            merged[-1]["content"] = left_blocks + right_blocks
        else:
            merged.append(message)
    return merged


def _openai_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(item.get("text") or "") if isinstance(item, dict) else str(item)
            for item in content
        ).strip()
    return str(content or "")
