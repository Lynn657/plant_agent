from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


class TodoManager:
    def __init__(self):
        self.items: list[dict[str, str]] = []

    def update(self, items: list[dict[str, Any]]) -> str:
        if not isinstance(items, list):
            raise ValueError("items 必须是数组")
        if len(items) > 20:
            raise ValueError("最多允许 20 个待办")
        validated = []
        for index, item in enumerate(items):
            text = str(item.get("text") or "").strip()
            status = str(item.get("status") or "pending").lower()
            item_id = str(item.get("id") or index + 1)
            if not text:
                raise ValueError(f"第 {index + 1} 项缺少 text")
            if status not in {"pending", "in_progress", "completed"}:
                raise ValueError(f"第 {index + 1} 项状态非法")
            validated.append({"id": item_id, "text": text[:180], "status": status})
        self.items = validated
        return self.render()

    def render(self) -> str:
        if not self.items:
            return "暂无待办。"
        markers = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}
        lines = [f"{markers[item['status']]} #{item['id']} {item['text']}" for item in self.items]
        done = sum(item["status"] == "completed" for item in self.items)
        lines.append(f"({done}/{len(self.items)} 完成)")
        return "\n".join(lines)


class MemoryStore:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        self.data: dict[str, Any] = {}
        if path.exists():
            try:
                self.data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self.data = {}

    def remember(self, key: str, value: str) -> str:
        key = str(key).strip()[:80]
        if not key:
            raise ValueError("记忆 key 不能为空")
        with self.lock:
            self.data[key] = str(value)[:1000]
            self._save()
        return f"已记住 {key} = {self.data[key]}"

    def recall(self, key: str = "") -> str:
        if key:
            value = self.data.get(key)
            return str(value) if value is not None else f"未找到记忆: {key}"
        return json.dumps(self.data, ensure_ascii=False, indent=2) if self.data else "暂无长期记忆。"

    def summary(self) -> str:
        if not self.data:
            return ""
        pairs = [f"{key}: {value}" for key, value in list(self.data.items())[:12]]
        return "；".join(pairs)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
