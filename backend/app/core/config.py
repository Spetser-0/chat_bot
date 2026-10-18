"""
app/core/config.py
──────────────────
Central configuration loaded from environment variables.
All settings are validated by Pydantic Settings on startup.
"""
from __future__ import annotations

from decimal import Decimal
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

    @property
    def async_database_url(self) -> str:
        """Ensure postgres URLs use asyncpg driver."""
        url = self.database_url
        if url.startswith("postgres://"):
            return "postgresql+asyncpg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            return "postgresql+asyncpg://" + url[len("postgresql://"):]
        return url

    # ── Session ──────────────────────────────────────────
    session_secret_key: str = Field(min_length=32)
    session_max_age_seconds: int = 86_400
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"

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
    auth_rate_limit_per_minute: int = 5
    chat_rate_limit_per_minute: int = 20
    chat_rate_limit_per_day: int = 200
    admin_rate_limit_per_minute: int = 30
    payments_rate_limit_per_minute: int = 10
    rate_limit_backend: Literal["memory", "redis"] = "memory"

    # ── Logging ──────────────────────────────────────────
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "console"

    # ── JWT Settings (Phase 2) ───────────────────────────
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # ── Redis (Phase 2) ──────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Encryption (Phase 2) ─────────────────────────────
    llm_master_encryption_key: str = ""

    # ── Payment Settings (Phase 2) ───────────────────────
    crypto_payment_provider: Literal["nowpayments", "cryptomus"] = "nowpayments"
    crypto_payment_api_key: str = ""
    crypto_payment_webhook_secret: str = ""

    # ── Referral Rewards (Phase 7) ──────────────────────
    referral_reward_percent: Decimal = Decimal("10")      # % of referred user's payment
    referral_reward_holding_days: int = 7                 # release delay (anti-fraud)

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
    settings = Settings()  # type: ignore[call-arg]
    
    # Fail fast if production secrets are missing
    if settings.is_production:
        if not settings.llm_master_encryption_key:
            raise ValueError("LLM_MASTER_ENCRYPTION_KEY is required in production")
        if not settings.crypto_payment_api_key:
            raise ValueError("CRYPTO_PAYMENT_API_KEY is required in production")
        if not settings.crypto_payment_webhook_secret:
            raise ValueError("CRYPTO_PAYMENT_WEBHOOK_SECRET is required in production")
    
    return settings
