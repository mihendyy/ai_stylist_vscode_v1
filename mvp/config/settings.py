"""Minimal settings loader for the MVP bot."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _load_env_file(path: str = ".env") -> None:
    """Populate environment variables from a .env file if present."""

    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(slots=True, frozen=True)
class MVPSettings:
    """Settings required for the simplified MVP."""

    bot_token: str
    aitunnel_api_key: str
    aitunnel_base_url: str
    aitunnel_chat_model: str = "gpt-4o"
    aitunnel_image_model: str = "gemini-2.5-flash-image"
    aitunnel_stt_model: str = "whisper-1"
    storage_root: str = "storage/users"
    generated_root: str = "storage/generated"
    request_timeout: float = 60.0


def _build_settings() -> MVPSettings:
    _load_env_file()
    return MVPSettings(
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        aitunnel_api_key=os.getenv("AITUNNEL_API_KEY", ""),
        aitunnel_base_url=os.getenv("AITUNNEL_BASE_URL", "https://api.aitunnel.ru/v1"),
        aitunnel_chat_model=os.getenv("MVP_CHAT_MODEL", os.getenv("AITUNNEL_CHAT_MODEL", "gpt-4o")),
        aitunnel_image_model=os.getenv(
            "MVP_IMAGE_MODEL",
            os.getenv("AITUNNEL_IMAGE_MODEL", "gemini-2.5-flash-image"),
        ),
        aitunnel_stt_model=os.getenv("MVP_STT_MODEL", "whisper-1"),
        storage_root=os.getenv("MVP_STORAGE_ROOT", "storage/users"),
        generated_root=os.getenv("MVP_GENERATED_ROOT", "storage/generated"),
        request_timeout=float(os.getenv("MVP_REQUEST_TIMEOUT", "60")),
    )


@lru_cache(maxsize=1)
def get_settings() -> MVPSettings:
    """Return cached settings instance."""

    return _build_settings()
