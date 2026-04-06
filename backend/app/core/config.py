from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://mataLmod:mataLmod_dev@localhost:5432/mataLmod",
        description="Async SQLAlchemy connection string (asyncpg driver).",
    )

    # ── Redis / Celery ────────────────────────────────────────
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # ── Anthropic ─────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = Field(default="")

    # ── Security ──────────────────────────────────────────────
    SECRET_KEY: str = Field(default="CHANGE_ME_IN_PRODUCTION")

    # ── Admin ─────────────────────────────────────────────────
    # Bearer token required for /api/v1/admin/* endpoints.
    # Generate: python -c "import secrets; print(secrets.token_hex(32))"
    ADMIN_API_KEY: str = Field(default="CHANGE_ME_IN_PRODUCTION")

    # ── Observability ─────────────────────────────────────────
    # Set to a valid Sentry DSN in production; leave empty to disable.
    SENTRY_DSN: str = Field(default="")
    # Fraction of transactions to send to Sentry APM (0.0–1.0).
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=0.1)

    # ── Application ───────────────────────────────────────────
    ENVIRONMENT: str = Field(default="development")
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:3000"])

    # ── Scraper ───────────────────────────────────────────────
    SCRAPER_RATE_LIMIT_SECONDS: int = Field(default=2)
    SCRAPER_MAX_RETRIES: int = Field(default=3)
    ANOMALY_CHECKSUM_THRESHOLD: float = Field(default=0.30)

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()
