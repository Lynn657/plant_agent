from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = APP_ROOT / "data"
SESSION_DIR = DATA_DIR / "sessions"
WEB_DIR = APP_ROOT / "web"
SKILLS_DIR = APP_ROOT / "skills"
CONFIG_DIR = APP_ROOT / "config"


def load_dotenv(path: Path | None = None) -> None:
    dotenv = path or (APP_ROOT / ".env")
    if not dotenv.exists():
        return
    for raw_line in dotenv.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(slots=True)
class AppConfig:
    provider: str
    api_key: str
    base_url: str
    model: str
    anthropic_version: str
    max_rounds: int
    compact_threshold: int
    request_timeout: int
    host: str
    port: int

    @property
    def llm_ready(self) -> bool:
        return self.provider in {"openai", "anthropic"} and bool(self.model) and bool(self.api_key)

    @property
    def public_status(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "model": self.model if self.llm_ready else "离线模板",
            "llm_ready": self.llm_ready,
            "offline_mode": not self.llm_ready,
        }


def get_config() -> AppConfig:
    load_dotenv()
    explicit_provider = os.getenv("PLANT_AGENT_PROVIDER", "").strip().lower()
    openai_key = os.getenv("PLANT_AGENT_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    anthropic_key = os.getenv("PLANT_AGENT_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "")
    if not explicit_provider:
        explicit_provider = "anthropic" if anthropic_key else "openai" if openai_key else "offline"
    if explicit_provider not in {"openai", "anthropic", "offline"}:
        explicit_provider = "offline"

    if explicit_provider == "anthropic":
        api_key = anthropic_key
        base_url = (
            os.getenv("PLANT_AGENT_BASE_URL")
            or os.getenv("ANTHROPIC_BASE_URL")
            or "https://api.anthropic.com"
        ).rstrip("/")
        model = os.getenv("PLANT_AGENT_MODEL") or os.getenv("MODEL_ID", "")
        if base_url.endswith("/v1"):
            base_url = base_url[:-3].rstrip("/")
    elif explicit_provider == "openai":
        api_key = openai_key
        base_url = (
            os.getenv("PLANT_AGENT_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        model = os.getenv("PLANT_AGENT_MODEL") or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    else:
        api_key = ""
        base_url = ""
        model = ""

    try:
        max_rounds = max(3, min(30, int(os.getenv("PLANT_AGENT_MAX_ROUNDS", "14"))))
    except ValueError:
        max_rounds = 14
    try:
        compact_threshold = max(12000, int(os.getenv("PLANT_AGENT_COMPACT_THRESHOLD", "45000")))
    except ValueError:
        compact_threshold = 45000
    try:
        request_timeout = max(10, int(os.getenv("PLANT_AGENT_TIMEOUT", "120")))
    except ValueError:
        request_timeout = 120
    try:
        port = max(1024, min(65535, int(os.getenv("PLANT_AGENT_PORT", "8765"))))
    except ValueError:
        port = 8765
    return AppConfig(
        provider=explicit_provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
        anthropic_version=os.getenv("PLANT_AGENT_ANTHROPIC_VERSION", "2023-06-01"),
        max_rounds=max_rounds,
        compact_threshold=compact_threshold,
        request_timeout=request_timeout,
        host=os.getenv("PLANT_AGENT_HOST", "127.0.0.1"),
        port=port,
    )


def ensure_directories() -> None:
    for path in (DATA_DIR, SESSION_DIR):
        path.mkdir(parents=True, exist_ok=True)
