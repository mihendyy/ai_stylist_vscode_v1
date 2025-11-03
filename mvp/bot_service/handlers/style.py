"""Handlers that capture long-term user preferences."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from mvp.bot_service.context import BotContext
from mvp.bot_service.filters import StageFilter
from mvp.bot_service.state_machine import ConversationState
from mvp.bot_service.voice_processor import VoiceProcessor
from mvp.logic import PreferenceExtractionError
from mvp.storage import UserProfile


def setup(router: Router, context: BotContext, voice_processor: VoiceProcessor) -> None:
    """Register style preference handlers."""

    @router.message(Command("style"))
    async def request_preferences(message: Message) -> None:
        profile = await context.storage.load(str(message.from_user.id))
        await context.state_machine.set_state(profile, ConversationState.AWAITING_PREFERENCES)
        await message.answer("Опиши словами или голосом, какой стиль тебе нравится.")

    @router.message(StageFilter(context, ConversationState.AWAITING_PREFERENCES), F.voice)
    async def handle_voice_preferences(message: Message, profile: UserProfile) -> None:
        transcript = await voice_processor.transcribe(message)
        if not transcript:
            await message.answer("Не удалось распознать голос. Попробуй текстом.")
            return
        await _store_preferences(message, context, profile, transcript)

    @router.message(StageFilter(context, ConversationState.AWAITING_PREFERENCES), F.text)
    async def handle_text_preferences(message: Message, profile: UserProfile) -> None:
        await _store_preferences(message, context, profile, message.text or "")


async def _store_preferences(message: Message, context: BotContext, profile, text: str) -> None:
    if not text.strip():
        await message.answer("Напиши хотя бы пару слов о предпочтениях.")
        return
    try:
        parsed = await context.logic.update_preferences(profile, text)
    except PreferenceExtractionError as exc:
        await message.answer(str(exc))
        return
    await context.state_machine.set_state(profile, ConversationState.READY)
    await message.answer(
        "Записала предпочтения. Когда будешь готов, используй команду /outfit_today.",
    )
