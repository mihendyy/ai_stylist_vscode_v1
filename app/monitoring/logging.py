"""Logging configuration module."""

from __future__ import annotations

import logging

from app.config.settings import get_settings


def configure_logging() -> None:
    """Configure root logger according to project conventions."""

    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
