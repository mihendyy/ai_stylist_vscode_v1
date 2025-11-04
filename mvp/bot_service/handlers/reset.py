"""Handler that clears stored user data."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from mvp.bot_service.context import BotContext
from mvp.bot_service.state_machine import ConversationState


def setup(router: Router, context: BotContext) -> None:
    """Register /reset handler."""

    @router.message(Command("reset"))
    async def handle_reset(message: Message) -> None:
        user_id = str(message.from_user.id)
        await context.storage.reset_user(user_id)
        profile = await context.storage.load(user_id)
        await context.state_machine.set_state(profile, ConversationState.AWAITING_SELFIE)
        await message.answer("Все данные очищены. Пришли селфи, чтобы начать заново.")
