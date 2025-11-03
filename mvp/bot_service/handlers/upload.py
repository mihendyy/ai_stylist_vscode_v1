"""Handlers responsible for media uploads and garment categorisation."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from aiogram import F, Router
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import Command
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

from mvp.bot_service.context import BotContext
from mvp.bot_service.filters import StageFilter
from mvp.bot_service.state_machine import ConversationState
from mvp.storage import UserProfile

CATEGORY_ALIASES = {
    "верх": "top",
    "топ": "top",
    "футболка": "top",
    "низ": "bottom",
    "юбка": "bottom",
    "брюки": "bottom",
    "джинсы": "bottom",
    "обувь": "shoes",
    "ботинки": "shoes",
    "кроссовки": "shoes",
    "аксессуар": "accessories",
    "аксессуары": "accessories",
    "сумка": "accessories",
    "ремень": "accessories",
    "верхняя одежда": "outerwear",
    "куртка": "outerwear",
    "пальто": "outerwear",
}

CATEGORY_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Верх"), KeyboardButton(text="Низ")],
        [KeyboardButton(text="Обувь"), KeyboardButton(text="Аксессуар")],
        [KeyboardButton(text="Верхняя одежда")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="Выберите категорию вещи",
)


def setup(router: Router, context: BotContext) -> None:
    """Register media upload handlers."""

    @router.message(Command("upload"))
    async def handle_upload_command(message: Message) -> None:
        profile = await context.storage.load(str(message.from_user.id))
        await context.state_machine.set_state(profile, ConversationState.AWAITING_GARMENT)
        await message.answer(
            "Пришли фото вещей по одной. После каждого фото выбери категорию.",
            reply_markup=ReplyKeyboardRemove(),
        )

    @router.message(F.photo)
    async def handle_photo(message: Message) -> None:
        user_id = str(message.from_user.id)
        profile = await context.storage.load(user_id)
        state = context.state_machine.current(profile)

        file = message.photo[-1]
        try:
            file_info = await message.bot.get_file(file.file_id)
            file_stream = await message.bot.download_file(file_info.file_path)
        except TelegramNetworkError:
            await message.answer("Не получилось скачать фото с серверов Telegram. Попробуйте ещё раз.")
            return

        data = file_stream.read()
        file_stream.close()

        user_dir, _ = context.storage.ensure_user_dirs(user_id)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        if state == ConversationState.AWAITING_SELFIE:
            selfie_path = user_dir / f"selfie_{timestamp}.jpg"
            await asyncio.to_thread(selfie_path.write_bytes, data)
            await context.storage.set_selfie(profile, str(selfie_path))
            await context.state_machine.set_state(profile, ConversationState.AWAITING_GARMENT)
            await message.answer(
                "Селфи сохранено. Теперь пришли одежду из гардероба по одной фотографии.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        garment_path = user_dir / f"garment_{timestamp}.jpg"
        await asyncio.to_thread(garment_path.write_bytes, data)
        await context.storage.set_pending_item(profile, str(garment_path))
        await context.state_machine.set_state(profile, ConversationState.AWAITING_CATEGORY)
        await message.answer(
            "Фото вещи сохранено. Выберите категорию на клавиатуре.",
            reply_markup=CATEGORY_KEYBOARD,
        )

    @router.message(StageFilter(context, ConversationState.AWAITING_CATEGORY), F.text)
    async def handle_category(message: Message, profile: UserProfile) -> None:
        category = _normalize_category(message.text or "")
        if not category:
            await message.answer(
                "Не распознала категорию. Выберите вариант на клавиатуре.",
                reply_markup=CATEGORY_KEYBOARD,
            )
            return

        if not profile.pending_item_path:
            await context.state_machine.set_state(profile, ConversationState.AWAITING_GARMENT)
            await message.answer("Похоже, новое фото не ожидается. Пришли следующую вещь.")
            return

        await context.storage.add_garment(profile, category, profile.pending_item_path)
        await context.storage.set_pending_item(profile, None)
        await context.state_machine.set_state(profile, ConversationState.AWAITING_GARMENT)
        await message.answer(
            "Категория сохранена. Пришли следующую вещь или команду /style для описания предпочтений.",
            reply_markup=ReplyKeyboardRemove(),
        )


def _normalize_category(raw: str) -> Optional[str]:
    normalized = raw.strip().lower()
    return CATEGORY_ALIASES.get(normalized)
