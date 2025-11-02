"""Application configuration powered by environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised project settings loaded from the .env file and OS environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )

    environment: Literal["dev", "test", "prod"] = Field(
        default="dev",
        description="Runtime environment flag used for environment-aware decisions.",
    )
    log_level: str = Field(default="INFO", description="Application logging level.")

    telegram_bot_token: str = Field(
        default="",
        description="Telegram bot token issued by BotFather.",
    )
    kie_ai_api_key: str = Field(
        default="",
        description="API key for KIE AI image services.",
    )
    aitunnel_api_key: str = Field(
        default="",
        description="API key used to access the chat completion provider.",
    )

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/app.db",
        description="SQLAlchemy-compatible database DSN.",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string for caching and queues.",
    )
    media_root: str = Field(
        default="data/media",
        description="Filesystem path used to store user-uploaded media in development.",
    )

    aitunnel_base_url: str = Field(
        default="https://api.aitunnel.ai/v1",
        description="Base URL for the dialog provider.",
    )
    aitunnel_health_path: str = Field(
        default="/status",
        description="Relative path used for connectivity checks to AITunnel.",
    )
    kie_base_url: str = Field(
        default="https://api.kie.ai/v1",
        description="Base URL for the KIE AI image services.",
    )
    kie_health_path: str = Field(
        default="/status",
        description="Relative path used for connectivity checks to KIE AI.",
    )
    weather_api_key: str = Field(
        default="",
        description="Optional weather provider token (P2 feature).",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance to avoid re-parsing the .env file."""

    return Settings()  # type: ignore[call-arg]
