"""Start command handler."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from mvp.bot_service.context import BotContext
from mvp.bot_service.state_machine import ConversationState


def setup(router: Router, context: BotContext) -> None:
    """Register /start handler."""

    @router.message(CommandStart())
    async def handle_start(message: Message) -> None:
        user_id = str(message.from_user.id)
        profile = await context.storage.load(user_id)
        await context.state_machine.set_state(profile, ConversationState.AWAITING_SELFIE)
        await message.answer(
            "Привет! Я помогу подобрать образ. Пришли селфи в полный рост, "
            "а затем по очереди добавь вещи из гардероба.",
        )
