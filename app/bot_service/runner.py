"""Entry point for launching the Telegram bot."""

from __future__ import annotations

import asyncio
import contextlib

from app.bot_service.handler import TelegramBot
from app.db.session import init_db


async def main() -> None:
    """Prepare infrastructure and start polling."""

    await init_db()
    bot = TelegramBot()
    try:
        await bot.start()
    finally:
        with contextlib.suppress(Exception):
            await bot.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
