"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _load_env_file(path: str = ".env") -> None:
    """Populate os.environ from the provided .env file if it exists."""

    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    """Centralised project settings based on OS environment variables."""

    environment: str = "dev"
    log_level: str = "INFO"

    telegram_bot_token: str = ""
    aitunnel_api_key: str = ""

    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    redis_url: str = "redis://localhost:6379/0"
    media_root: str = "data/media"

    aitunnel_base_url: str = "https://api.aitunnel.ru/v1"
    aitunnel_health_path: str = "/models"
    aitunnel_chat_model: str = "gpt-5-mini"
    aitunnel_image_model: str = "gemini-2.5-flash-image"
    aitunnel_image_size: str = "1024x1536"
    aitunnel_image_quality: str = "medium"
    aitunnel_image_moderation: str = "low"

    weather_api_key: str = ""


def _build_settings() -> Settings:
    _load_env_file()

    return Settings(
        environment=os.getenv("ENVIRONMENT", "dev"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        aitunnel_api_key=os.getenv("AITUNNEL_API_KEY", ""),
        database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/app.db"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        media_root=os.getenv("MEDIA_ROOT", "data/media"),
        aitunnel_base_url=os.getenv("AITUNNEL_BASE_URL", "https://api.aitunnel.ru/v1"),
        aitunnel_health_path=os.getenv("AITUNNEL_HEALTH_PATH", "/models"),
        aitunnel_chat_model=os.getenv("AITUNNEL_CHAT_MODEL", "gpt-5-mini"),
        aitunnel_image_model=os.getenv("AITUNNEL_IMAGE_MODEL", "gemini-2.5-flash-image"),
        aitunnel_image_size=os.getenv("AITUNNEL_IMAGE_SIZE", "1024x1536"),
        aitunnel_image_quality=os.getenv("AITUNNEL_IMAGE_QUALITY", "medium"),
        aitunnel_image_moderation=os.getenv("AITUNNEL_IMAGE_MODERATION", "low"),
        weather_api_key=os.getenv("WEATHER_API_KEY", ""),
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance to avoid re-reading configuration."""

    return _build_settings()
