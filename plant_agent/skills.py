from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class SkillRegistry:
    def __init__(self, root: Path):
        self.root = root
        self.skills: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.root.exists():
            return
        for path in sorted(self.root.rglob("SKILL.md")):
            text = path.read_text(encoding="utf-8")
            meta, body = self._frontmatter(text)
            name = str(meta.get("name") or path.parent.name)
            self.skills[name] = {
                "name": name,
                "description": str(meta.get("description") or "专用知识"),
                "tags": str(meta.get("tags") or ""),
                "body": body,
                "path": str(path),
            }

    @staticmethod
    def _frontmatter(text: str) -> tuple[dict[str, str], str]:
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
        if not match:
            return {}, text.strip()
        meta: dict[str, str] = {}
        for line in match.group(1).splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip("\"'")
        return meta, match.group(2).strip()

    def catalog(self) -> str:
        if not self.skills:
            return "(没有可用技能)"
        return "\n".join(
            f"- {skill['name']}: {skill['description']}"
            for skill in self.skills.values()
        )

    def public_catalog(self) -> list[dict[str, str]]:
        return [
            {
                "name": skill["name"],
                "description": skill["description"],
                "tags": skill["tags"],
            }
            for skill in self.skills.values()
        ]

    def load(self, name: str) -> str:
        skill = self.skills.get(name)
        if not skill:
            return f"未知技能 '{name}'。可用技能: {', '.join(self.skills)}"
        return f'<skill name="{name}">\n{skill["body"]}\n</skill>'
