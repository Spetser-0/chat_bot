"""
app/core/config.py
──────────────────
Central configuration loaded from environment variables.
All settings are validated by Pydantic Settings on startup.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    app_secret_key: str = Field(min_length=32)
    app_debug: bool = False
    app_allowed_origins: str = "http://localhost:5173"
    app_name: str = "Spetser AI"
    app_version: str = "0.1.0"

    # ── Database ─────────────────────────────────────────
    database_url: str

    # ── Session ──────────────────────────────────────────
    session_secret_key: str = Field(min_length=32)
    session_max_age_seconds: int = 86_400

    # ── Supabase Storage ─────────────────────────────────
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    storage_bucket_deliverables: str = "spetser-deliverables"
    storage_tmp_dir: str = "/tmp/spetser"

    # ── AI Provider Keys ─────────────────────────────────
    anthropic_api_key: str = ""
    google_gemini_api_key: str = ""
    openai_api_key: str = ""
    qwen_api_key: str = ""
    kimi_api_key: str = ""

    # ── Developer Auth ───────────────────────────────────
    developer_email: str = "dev@example.com"
    developer_password_hash: str = ""

    # ── Rate Limits ──────────────────────────────────────
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10

    # ── Logging ──────────────────────────────────────────
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "console"

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse comma-separated origins string into list."""
        return [o.strip() for o in self.app_allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()  # type: ignore[call-arg]
