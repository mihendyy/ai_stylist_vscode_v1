"""Command handler that orchestrates outfit generation."""

from __future__ import annotations

from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message, ReplyKeyboardRemove

from mvp.bot_service.context import BotContext
from mvp.bot_service.filters import StageFilter
from mvp.bot_service.state_machine import ConversationState
from mvp.logic import OutfitPlanningError
from mvp.storage import UserProfile

POSITIVE_FEEDBACK = {"👍", "нравится", "класс"}
NEGATIVE_FEEDBACK = {"👎", "не нравится", "плохо"}


def setup(router: Router, context: BotContext) -> None:
    """Register handlers related to outfit generation."""

    @router.message(Command("outfit_today"))
    async def request_daily_context(message: Message) -> None:
        profile = await context.storage.load(str(message.from_user.id))
        await context.state_machine.set_state(profile, ConversationState.AWAITING_DAILY_CONTEXT)
        await message.answer(
            "Расскажи, куда собираешься и какие есть пожелания (стиль, погода).",
            reply_markup=ReplyKeyboardRemove(),
        )

    @router.message(StageFilter(context, ConversationState.AWAITING_DAILY_CONTEXT), F.text)
    async def handle_daily_context(message: Message, profile: UserProfile) -> None:
        text = (message.text or "").strip()
        await _process_daily_request(message, context, profile, text)

    @router.message(StageFilter(context, ConversationState.READY), F.text)
    async def handle_feedback(message: Message, profile: UserProfile) -> None:
        text = (message.text or "").strip()
        lowered = text.lower()
        if lowered in POSITIVE_FEEDBACK:
            await context.storage.add_feedback(profile, "positive", "")
            await message.answer("Спасибо за отзыв! Обращайся, когда нужно.")
            return
        if lowered in NEGATIVE_FEEDBACK:
            await context.storage.add_feedback(profile, "negative", text)
            await message.answer("Записала замечание. Постараюсь учесть в следующий раз.")
            return


async def _process_daily_request(message: Message, context: BotContext, profile, text: str) -> None:
    if not text:
        await message.answer("Опиши хотя бы пару слов о сегодняшнем запросе.")
        return
    await context.storage.update_daily_context(
        profile,
        {
            "notes": text,
        },
    )
    try:
        result = await context.logic.generate_outfit(profile, extra_context={"notes": text})
    except OutfitPlanningError as exc:
        await message.answer(str(exc))
        return

    await context.state_machine.set_state(profile, ConversationState.READY)
    await message.answer(result.summary)

    if result.image_path and Path(result.image_path).exists():
        photo = FSInputFile(result.image_path)
        await message.answer_photo(photo, caption="Вот твой образ на сегодня!")
    elif result.image_url:
        await message.answer_photo(result.image_url, caption="Вот твой образ на сегодня!")
    else:
        await message.answer("Не удалось получить изображение, но рекомендации всё равно сохранены.")

    await message.answer("Понравилось? Отправь 👍 или 👎 и уточнение, если хочешь.")
