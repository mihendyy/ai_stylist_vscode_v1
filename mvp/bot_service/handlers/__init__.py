"""Register message and command handlers."""

from __future__ import annotations

from aiogram import Router

from mvp.bot_service.context import BotContext
from mvp.bot_service.voice_processor import VoiceProcessor

from . import outfit_today, start, style, upload


def setup_handlers(router: Router, context: BotContext, voice_processor: VoiceProcessor) -> None:
    """Attach all handler groups to the provided router."""

    start.setup(router, context)
    upload.setup(router, context)
    style.setup(router, context, voice_processor)
    outfit_today.setup(router, context)
