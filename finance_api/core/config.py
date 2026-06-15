"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from finance_api.core.product import DEFAULT_AGENT_MODEL, DEFAULT_MINI_APP_URL


class Settings(BaseSettings):
    """All config comes from env vars. Required fields fail loud at startup."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "local"
    log_level: str = "INFO"

    database_url: str
    db_pool_size: int = 5
    db_max_overflow: int = 10

    monobank_token: str
    app_secret: str | None = None
    sync_interval_hours: int = 1
    monobank_fetch_days: int = 32

    partner_name_pattern: str = ""  # legacy regex for partner transfers
    fop_account_ids: str = ""  # comma-separated Monobank account IDs

    telegram_bot_token: str | None = None
    telegram_owner_id: int
    telegram_allowed_user_ids: str = ""
    telegram_chat_id: int | None = None
    telegram_finance_topic_id: int | None = None

    mini_app_url: str = DEFAULT_MINI_APP_URL

    openrouter_api_key: str
    agent_model: str = DEFAULT_AGENT_MODEL


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
