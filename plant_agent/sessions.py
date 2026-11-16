from __future__ import annotations

import json
import re
import secrets
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


class SessionStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def new_id(self) -> str:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"{stamp}-{secrets.token_hex(3)}"

    def save(self, session: dict[str, Any]) -> None:
        session_id = self._safe_id(str(session["id"]))
        session["id"] = session_id
        session["updated_at"] = datetime.now().isoformat(timespec="seconds")
        target = self.root / session_id
        with self.lock:
            target.mkdir(parents=True, exist_ok=True)
            (target / "session.json").write_text(
                json.dumps(session, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            if session.get("diagram"):
                (target / "diagram.json").write_text(
                    json.dumps(session["diagram"], ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            if session.get("svg"):
                (target / "diagram.svg").write_text(str(session["svg"]), encoding="utf-8")
            if session.get("mermaid"):
                (target / "diagram.mmd").write_text(str(session["mermaid"]), encoding="utf-8")

    def load(self, session_id: str) -> dict[str, Any] | None:
        path = self.root / self._safe_id(session_id) / "session.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def list(self, limit: int = 30) -> list[dict[str, Any]]:
        rows = []
        for path in self.root.glob("*/session.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            rows.append(
                {
                    "id": data.get("id", path.parent.name),
                    "title": data.get("title") or data.get("prompt", "未命名图表")[:50],
                    "kind": (data.get("diagram") or {}).get("kind", ""),
                    "updated_at": data.get("updated_at", ""),
                }
            )
        rows.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
        return rows[:limit]

    def append_transcript(self, session_id: str, event: dict[str, Any]) -> None:
        target = self.root / self._safe_id(session_id)
        target.mkdir(parents=True, exist_ok=True)
        with self.lock, (target / "transcript.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

    @staticmethod
    def _safe_id(value: str) -> str:
        clean = re.sub(r"[^A-Za-z0-9_-]", "", value)
        if not clean or clean != value:
            raise ValueError("无效的会话 id")
        return clean[:80]
