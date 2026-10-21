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

from pydantic import Field, field_validator, ValidationInfo
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

    # ── Email & Verification (SMTP) ──────────────────────
    smtp_host: str = Field(
        default="",
        description="SMTP server hostname (e.g., smtp.gmail.com)"
    )
    smtp_port: int = Field(
        default=587,
        description="SMTP server port (587 for TLS, 465 for SSL)"
    )
    smtp_user: str = Field(
        default="",
        description="SMTP username (email address)"
    )
    smtp_password: str = Field(
        default="",
        description="SMTP password or app-specific password"
    )
    smtp_from: str = Field(
        default="noreply@spetser.ai",
        description="Sender email address"
    )
    smtp_use_tls: bool = Field(
        default=True,
        description="Use TLS for SMTP connection"
    )

    @field_validator("smtp_user", "smtp_password", "smtp_host")
    @classmethod
    def validate_smtp_in_production(cls, v: str, info: ValidationInfo) -> str:
        """Fail fast in production if SMTP is not configured."""
        values = info.data
        app_env = values.get("app_env", "development")

        if app_env == "production" and not v:
            field_name = info.field_name
            raise ValueError(
                f"{field_name} is required in production. "
                f"Set {field_name.upper()} environment variable."
            )
        return v

    # ── Password Reset & Auth Enhancements ───────────────
    reset_token_secret: str = ""
    default_new_user_credits: int = 300

    @property
    def DEBUG(self) -> bool:
        return self.app_debug or self.app_env != "production"

    @property
    def SMTP_HOST(self) -> str:
        return self.smtp_host

    @property
    def SMTP_PORT(self) -> int:
        return self.smtp_port

    @property
    def SMTP_USER(self) -> str:
        return self.smtp_user

    @property
    def SMTP_PASSWORD(self) -> str:
        return self.smtp_password

    @property
    def SMTP_FROM(self) -> str:
        return self.smtp_from

    @property
    def smtp_tls(self) -> bool:
        return self.smtp_use_tls

    @property
    def SMTP_TLS(self) -> bool:
        return self.smtp_use_tls

    @property
    def SMTP_USE_TLS(self) -> bool:
        return self.smtp_use_tls

    @property
    def RESET_TOKEN_SECRET(self) -> str:
        return self.reset_token_secret or self.app_secret_key

    @property
    def DEFAULT_NEW_USER_CREDITS(self) -> int:
        return self.default_new_user_credits

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
