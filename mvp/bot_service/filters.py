"""Custom aiogram filters used in the MVP bot."""

from __future__ import annotations

from typing import Any

from aiogram.filters import BaseFilter
from aiogram.types import Message

from mvp.bot_service.context import BotContext
from mvp.bot_service.state_machine import ConversationState
from mvp.storage import UserProfile


class StageFilter(BaseFilter):
    """Matches messages when the user's profile is at the expected stage."""

    def __init__(self, context: BotContext, expected: ConversationState) -> None:
        self._context = context
        self._expected = expected

    async def __call__(self, message: Message) -> bool | dict[str, Any]:
        user_id = str(message.from_user.id)
        profile = await self._context.storage.load(user_id)
        if self._context.state_machine.current(profile) == self._expected:
            return {"profile": profile}
        return False
