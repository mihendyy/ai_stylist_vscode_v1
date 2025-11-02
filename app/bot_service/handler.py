"""Telegram bot lifecycle management using Aiogram."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    BufferedInputFile,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot_service.voice_processor import VoiceProcessor
from app.config.settings import get_settings
from app.db import models
from app.db.session import AsyncSessionFactory
from app.nlp.intent import IntentClassifier
from app.services.outfit import OutfitOrchestrator
from app.services.stages import OnboardingStage
from app.services.wardrobe import WardrobeService
from app.storage.backend import LocalStorage


class TelegramBot:
    """Encapsulates bot wiring, handlers and background startup logic."""

    DONE_KEYWORDS = {"готово", "готова", "done", "готов"}
    CATEGORY_ALIASES = {
        "верх": "top",
        "топ": "top",
        "футболка": "top",
        "рубашка": "top",
        "низ": "bottom",
        "юбка": "bottom",
        "брюки": "bottom",
        "джинсы": "bottom",
        "обувь": "shoes",
        "ботинки": "shoes",
        "кроссовки": "shoes",
        "аксессуар": "accessory",
        "аксессуары": "accessory",
        "ремень": "accessory",
        "сумка": "accessory",
        "верхняя одежда": "outerwear",
        "куртка": "outerwear",
        "пальто": "outerwear",
    }

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.telegram_bot_token:
            raise RuntimeError("Telegram bot token is missing.")

        self._bot = Bot(token=settings.telegram_bot_token, parse_mode=ParseMode.HTML)
        self._dispatcher = Dispatcher()
        self._voice_processor = VoiceProcessor()
        storage_root = Path(settings.media_root)
        self._wardrobe_service = WardrobeService(LocalStorage(storage_root))
        self._intent_classifier = IntentClassifier()
        self._orchestrator = OutfitOrchestrator(self._wardrobe_service)
        self._category_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="Верх"),
                    KeyboardButton(text="Низ"),
                ],
                [
                    KeyboardButton(text="Обувь"),
                    KeyboardButton(text="Аксессуар"),
                ],
                [
                    KeyboardButton(text="Верхняя одежда"),
                ],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
            input_field_placeholder="Выберите категорию вещи",
        )
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register core command and message handlers."""

        @self._dispatcher.message(CommandStart())
        async def handle_start(message: Message) -> None:
            """Welcome message with a concise value proposition."""

            async with AsyncSessionFactory() as session:
                user = await self._wardrobe_service.ensure_user(
                    session,
                    telegram_id=str(message.from_user.id),
                    language=message.from_user.language_code,
                )

                await message.answer(
                    "Привет! Я твой ИИ-стилист. Помогу собрать цифровой гардероб и подобрать образ.",
                )
                await self._send_stage_hint(message, OnboardingStage(user.onboarding_stage))

        @self._dispatcher.message(F.voice)
        async def handle_voice(message: Message) -> None:
            """Process incoming voice messages and respond with extracted intent."""

            transcript = await self._voice_processor.transcribe_voice(message)
            if not transcript:
                await message.answer("Не удалось распознать голосовое сообщение.")
                return
            await self._process_text(message, transcript)

        @self._dispatcher.message(F.photo)
        async def handle_photo(message: Message) -> None:
            """Persist uploaded garment photos."""

            photo = message.photo[-1]
            file = await message.bot.get_file(photo.file_id)
            file_stream = await message.bot.download_file(file.file_path)
            file_bytes = file_stream.read()
            file_stream.close()

            async with AsyncSessionFactory() as session:
                user = await self._wardrobe_service.ensure_user(
                    session,
                    telegram_id=str(message.from_user.id),
                    language=message.from_user.language_code,
                )
                stage = self._get_stage(user)

                if stage == OnboardingStage.AWAITING_SELFIE:
                    await self._wardrobe_service.save_selfie(
                        session,
                        user=user,
                        file_name=file.file_path or "selfie.jpg",
                        file_data=file_bytes,
                    )
                    await self._wardrobe_service.update_stage(
                        session,
                        user=user,
                        stage=OnboardingStage.AWAITING_GARMENTS,
                    )
                    await message.answer(
                        "Класс! Селфи сохранено. Теперь пришлите вещи из гардероба по одной фотографии.",
                    )
                    return

                if stage == OnboardingStage.AWAITING_GARMENT_CATEGORY:
                    await message.answer(
                        "Сначала выберите категорию для предыдущей вещи, затем отправляйте новые фото.",
                        reply_markup=self._category_keyboard,
                    )
                    return

                garment = await self._wardrobe_service.add_garment(
                    session,
                    user=user,
                    file_name=file.file_path or "garment.jpg",
                    file_data=file_bytes,
                )
                await self._wardrobe_service.set_pending_garment(
                    session,
                    user=user,
                    garment=garment,
                )
                await self._wardrobe_service.update_stage(
                    session,
                    user=user,
                    stage=OnboardingStage.AWAITING_GARMENT_CATEGORY,
                )

                await message.answer(
                    "Фото добавлено. Выберите тип вещи (верх, низ, обувь, аксессуар, верхняя одежда).",
                    reply_markup=self._category_keyboard,
                )

        @self._dispatcher.message(F.text)
        async def handle_text(message: Message) -> None:
            """React to free-form text commands."""

            await self._process_text(message, message.text)

    async def start(self) -> None:
        """Begin polling Telegram for updates."""

        await self._dispatcher.start_polling(self._bot)

    async def shutdown(self) -> None:
        """Gracefully close bot resources."""

        await self._bot.session.close()

    async def _process_text(self, message: Message, text: str) -> None:
        """Handle textual input according to the user's onboarding stage."""

        normalized_text = text.strip()
        lower_text = normalized_text.lower()

        async with AsyncSessionFactory() as session:
            user = await self._wardrobe_service.ensure_user(
                session,
                telegram_id=str(message.from_user.id),
                language=message.from_user.language_code,
            )
            stage = self._get_stage(user)

            if lower_text in {"/reset"}:
                await self._reset_user(session, user)
                await message.answer(
                    "Сессия сброшена. Давайте начнём заново — пришлите селфи.",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return

            if stage == OnboardingStage.AWAITING_SELFIE:
                await message.answer("Для начала пришлите селфи в полный рост.")
                return

            if stage == OnboardingStage.AWAITING_GARMENT_CATEGORY:
                category = self._normalize_category(lower_text)
                if not category:
                    await message.answer(
                        "Не распознала категорию. Пожалуйста, выберите вариант с клавиатуры.",
                        reply_markup=self._category_keyboard,
                    )
                    return

                pending = await self._wardrobe_service.get_pending_garment(session, user=user)
                if not pending:
                    await self._wardrobe_service.update_stage(
                        session,
                        user=user,
                        stage=OnboardingStage.AWAITING_GARMENTS,
                    )
                    await message.answer(
                        "Категории больше не ожидаются. Отправьте фото вещи или напишите «Готово».",
                        reply_markup=ReplyKeyboardRemove(),
                    )
                    return

                await self._wardrobe_service.assign_garment_label(
                    session,
                    garment_id=pending.id,
                    label=category,
                )
                await self._wardrobe_service.set_pending_garment(
                    session,
                    user=user,
                    garment=None,
                )

                next_stage = (
                    OnboardingStage.READY
                    if user.style_reference
                    else OnboardingStage.AWAITING_GARMENTS
                )
                await self._wardrobe_service.update_stage(
                    session,
                    user=user,
                    stage=next_stage,
                )

                await message.answer(
                    "Категория сохранена. Можете отправить следующую вещь или написать «Готово».",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return

            if stage == OnboardingStage.AWAITING_GARMENTS:
                if lower_text in self.DONE_KEYWORDS:
                    garments = await self._wardrobe_service.list_user_garments(session, user=user)
                    if not garments:
                        await message.answer(
                            "Пока нет ни одной вещи. Пришлите хотя бы одну фотографию из гардероба.",
                        )
                        return
                    await self._wardrobe_service.update_stage(
                        session,
                        user=user,
                        stage=OnboardingStage.AWAITING_STYLE,
                    )
                    await message.answer(
                        "Отлично! Теперь расскажите, какая стилистика вам близка. "
                        "Можно упомянуть любимых людей, бренды, настроение.",
                    )
                    return

                await message.answer(
                    "Отправьте фотографию вещи. Когда закончите, напишите «Готово».",
                )
                return

            if stage == OnboardingStage.AWAITING_STYLE:
                await self._wardrobe_service.update_style_reference(
                    session,
                    user=user,
                    style_reference=normalized_text,
                )
                await self._wardrobe_service.update_stage(
                    session,
                    user=user,
                    stage=OnboardingStage.READY,
                )
                await message.answer(
                    "Записала ваши предпочтения. Теперь запросите образ фразой «Что надеть сегодня?»",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return

            # READY or fallback branch
            parsed = self._intent_classifier.parse_message(normalized_text)
            if parsed.intent == "today_outfit":
                await message.answer(
                    "Подбираю образ — это может занять до минуты.",
                )
                try:
                    result = await self._orchestrator.build_outfit(session, user=user)
                except ValueError as error:
                    await message.answer(str(error))
                    return
                except Exception as exc:  # pragma: no cover - defensive fallback
                    await message.answer(
                        "Не получилось подготовить образ. Попробуйте немного позже.",
                    )
                    raise exc

                recommendation = result["recommendation"]
                await message.answer(recommendation.natural_text)
                if recommendation.reasons:
                    reasons_text = "\n".join(f"• {reason}" for reason in recommendation.reasons)
                    await message.answer(f"Почему так:\n{reasons_text}")
                if recommendation.missing_items:
                    missing = "\n".join(f"- {item}" for item in recommendation.missing_items)
                    await message.answer(f"В следующий раз можно добавить:\n{missing}")

                await self._send_generation_result(message, result["generation_result"])
                return

            await message.answer(
                "Чтобы получить рекомендации, напишите «Что надеть сегодня?» или добавьте новые вещи фото.",
            )

    async def _send_stage_hint(self, message: Message, stage: OnboardingStage) -> None:
        """Send user instructions for the current stage."""

        hints = {
            OnboardingStage.AWAITING_SELFIE: "Шаг 1 — пришлите селфи в полный рост при хорошем освещении.",
            OnboardingStage.AWAITING_GARMENTS: (
                "Шаг 2 — отправляйте вещи из гардероба по одной фотографии. "
                "Когда закончите, напишите «Готово»."
            ),
            OnboardingStage.AWAITING_STYLE: (
                "Шаг 3 — расскажите, какой стиль вам нравится: опишите словами или назовите референсы."
            ),
            OnboardingStage.READY: (
                "Теперь можно спросить «Что надеть сегодня?» — я подберу образ и покажу визуализацию."
            ),
        }
        hint = hints.get(stage)
        if hint:
            await message.answer(hint)

    def _normalize_category(self, text: str) -> str | None:
        """Map user input to canonical garment category."""

        return self.CATEGORY_ALIASES.get(text)

    def _get_stage(self, user: models.User) -> OnboardingStage:
        """Safely cast stored stage string to enum."""

        try:
            return OnboardingStage(user.onboarding_stage)
        except ValueError:  # pragma: no cover - safeguards inconsistent data
            return OnboardingStage.AWAITING_SELFIE

    async def _send_generation_result(self, message: Message, payload: dict[str, Any]) -> None:
        """Send generated image back to the user."""

        image_url = payload.get("image_url")
        if image_url:
            await message.answer_photo(image_url)
            return

        base64_image = payload.get("image_base64")
        if base64_image:
            try:
                image_bytes = base64.b64decode(base64_image)
            except ValueError:
                await message.answer("Получен некорректный формат изображения.")
                return
            await message.answer_photo(
                BufferedInputFile(image_bytes, filename="outfit.jpg"),
            )
            return

        await message.answer(
            "Изображение пока не готово. Я сообщу, как только смогу его получить.",
        )

    async def _reset_user(self, session: AsyncSession, user: models.User) -> None:
        """Reset onboarding data for the user."""

        garments = await self._wardrobe_service.list_user_garments(
            session,
            user=user,
            include_inactive=True,
        )
        for garment in garments:
            await session.delete(garment)

        selfie = await self._wardrobe_service.get_selfie(session, user=user)
        if selfie:
            await session.delete(selfie)

        await self._wardrobe_service.set_pending_garment(session, user=user, garment=None)
        await self._wardrobe_service.update_style_reference(session, user=user, style_reference="")
        await self._wardrobe_service.update_stage(
            session,
            user=user,
            stage=OnboardingStage.AWAITING_SELFIE,
        )
        await session.commit()
