from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable


class BackgroundJobs:
    """Small s08-style background runner with completion notifications."""

    def __init__(self, workers: int = 2):
        self.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="plant-agent")
        self.notifications: list[dict[str, Any]] = []

    def submit(self, name: str, fn: Callable, *args: Any, **kwargs: Any):
        return name, self.pool.submit(fn, *args, **kwargs)

    def collect(self, jobs: list[tuple[str, Any]]) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for name, future in jobs:
            try:
                results[name] = future.result(timeout=30)
                self.notifications.append({"job": name, "status": "completed"})
            except Exception as exc:
                results[name] = exc
                self.notifications.append({"job": name, "status": "failed", "error": str(exc)})
        return results

    def close(self) -> None:
        self.pool.shutdown(wait=False, cancel_futures=True)


class ReviewTeam:
    """Two fresh-context reviewers, coordinated like a tiny s09 review team."""

    ROLES = {
        "uml": (
            "你是 UML 语义评审员。检查关系箭头、抽象角色、时序顺序、状态出口和孤立节点。"
            "只列出需要修正的具体问题；没有问题时明确说“UML 结构通过”。"
        ),
        "domain": (
            "你是软件需求评审员。检查图中是否遗漏题目里的关键角色、规则、异常路径或业务对象。"
            "只列出具体遗漏与建议；没有问题时明确说“需求覆盖通过”。"
        ),
    }

    def __init__(self, provider):
        self.provider = provider

    def review(self, spec: dict[str, Any], focus: str = "") -> str:
        diagram = json.dumps(spec, ensure_ascii=False)[:30000]
        prompt = f"评审重点：{focus or '整体建模质量'}\n<diagram>{diagram}</diagram>"
        results: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="review-team") as pool:
            futures = {
                pool.submit(
                    self.provider.complete,
                    system,
                    [{"role": "user", "content": prompt}],
                    [],
                ): role
                for role, system in self.ROLES.items()
            }
            for future in as_completed(futures):
                role = futures[future]
                try:
                    response = future.result(timeout=60)
                    results[role] = response.text or "(无意见)"
                except Exception as exc:
                    results[role] = f"评审失败: {exc}"
        return (
            "【UML 评审】\n"
            + results.get("uml", "无结果")
            + "\n\n【需求评审】\n"
            + results.get("domain", "无结果")
        )
