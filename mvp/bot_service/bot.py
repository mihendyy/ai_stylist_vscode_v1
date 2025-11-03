"""Entrypoint for the MVP Telegram bot."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from pathlib import Path

from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode

from mvp.api import AITunnelClient
from mvp.bot_service.context import BotContext
from mvp.bot_service.handlers import setup_handlers
from mvp.bot_service.state_machine import StateMachine
from mvp.bot_service.voice_processor import VoiceProcessor
from mvp.config.settings import get_settings
from mvp.logic import StylistLogic
from mvp.storage import UserStorage

logger = logging.getLogger(__name__)


async def main() -> None:
    """Initialise dependencies and start polling Telegram."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    settings = get_settings()
    if not settings.bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")
    if not settings.aitunnel_api_key:
        raise RuntimeError("AITUNNEL_API_KEY is not configured.")

    storage = UserStorage(Path(settings.storage_root), Path(settings.generated_root))
    client = AITunnelClient(settings)
    logic = StylistLogic(settings, storage, client)
    state_machine = StateMachine(storage)
    voice_processor = VoiceProcessor(client)

    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)
    dispatcher = Dispatcher()
    router = Router()
    setup_handlers(router, BotContext(storage=storage, logic=logic, state_machine=state_machine), voice_processor)
    dispatcher.include_router(router)

    try:
        logger.info("Starting MVP bot polling.")
        await dispatcher.start_polling(bot)
    finally:
        with suppress(Exception):
            await bot.session.close()
        with suppress(Exception):
            await client.close()


if __name__ == "__main__":
    asyncio.run(main())
