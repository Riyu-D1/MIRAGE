"""MIRAGE settings — loaded from repo-root .env with offline-first fallbacks.

Every sponsor integration exposes an ``*_enabled`` flag. Code must check the
flag and degrade to SQLite / cached fixtures — never try/except to detect.
See AGENTS.md §5.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/backend/app/config.py -> repo root is parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Local services
    target_merchant_url: str = "http://localhost:8001"
    backend_url: str = "http://localhost:8000"
    mcp_server_url: str = "http://localhost:8002"

    # Sponsors (blank => offline fallback)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    grokbot_webhook_url: str = ""
    grokbot_api_key: str = ""
    tavily_api_key: str = ""
    companies_house_api_key: str = ""

    # Behaviour
    headless: bool = True
    artifacts_dir: str = "artifacts"

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def grokbot_enabled(self) -> bool:
        return bool(self.grokbot_webhook_url)

    @property
    def tavily_enabled(self) -> bool:
        return bool(self.tavily_api_key)

    @property
    def companies_house_enabled(self) -> bool:
        return bool(self.companies_house_api_key)

    @property
    def artifacts_path(self) -> Path:
        return REPO_ROOT / self.artifacts_dir

    @property
    def sqlite_path(self) -> Path:
        return self.artifacts_path / "mirage.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
