"""Outfit orchestration pipeline that coordinates LLM and image generation."""

from __future__ import annotations

import json
from typing import Any, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.imggen.generator_client import ImageGeneratorClient
from app.nlp.chatgpt_client import ChatGPTClient, RecommendationResponse
from app.services.wardrobe import WardrobeService

class OutfitOrchestrator:
    """Coordinates the conversation model with the image generation backend."""

    def __init__(self, wardrobe_service: WardrobeService) -> None:
        self._wardrobe_service = wardrobe_service

    async def _prepare_recommendation_payload(
        self,
        user: models.User,
        garments: Sequence[models.Garment],
    ) -> dict[str, Any]:
        """Compose payload expected by the ChatGPT client."""

        wardrobe_listing = [
            {
                "garment_id": garment.id,
                "label": garment.label or "неизвестно",
                "path": garment.storage_path,
            }
            for garment in garments
        ]
        style_reference = user.style_reference or "не указано"

        system_prompt = (
            "Ты — персональный стилист, который подбирает образы из гардероба пользователя. "
            "Отвечай ТОЛЬКО JSON объектом со следующей структурой: {\"suggested_outfit\": ["
            "{""garment_id"": int, ""description"": str}], \"natural_text\": str, "
            "\"reasons\": [str], \"missing_items\": [str] }. Используй garment_id из раздела "
            "wardrobe. Если подходящих вещей нет, верни пустой suggested_outfit и объясни это в "
            "natural_text. Не добавляй лишних полей и не используй Markdown."
        )
        user_prompt = {
            "style_reference": style_reference,
            "wardrobe": wardrobe_listing,
            "request": "Подбери образ из имеющихся вещей. Если чего-то не хватает — перечисли в missing_items.",
        }
        return {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
            ],
            "max_tokens": 1200,
        }

    def _pick_selected_garments(
        self,
        garments: Sequence[models.Garment],
        recommendation: RecommendationResponse,
    ) -> list[models.Garment]:
        """Return garments referenced in the recommendation (fallback to first items)."""

        id_candidates: list[int] = []
        for item in recommendation.suggested_outfit:
            for key in ("garment_id", "id"):
                raw_value = item.get(key)
                if raw_value is None:
                    continue
                try:
                    id_candidates.append(int(raw_value))
                except (ValueError, TypeError):
                    continue

        selected = [g for g in garments if g.id in id_candidates]
        if selected:
            return selected
        return list(garments[:2])

    async def build_outfit(
        self,
        session: AsyncSession,
        *,
        user: models.User,
    ) -> dict[str, Any]:
        """
        Generate full outfit recommendation and image.

        Returns a dictionary containing textual explanations and generator response.
        """

        selfie = await self._wardrobe_service.get_selfie(session, user=user)
        if not selfie:
            raise ValueError("Сначала нужно загрузить селфи.")

        garments = await self._wardrobe_service.list_user_garments(session, user=user)
        if not garments:
            raise ValueError("Гардероб пуст. Загрузите несколько вещей.")

        chat_payload = await self._prepare_recommendation_payload(user, garments)
        chat_client = ChatGPTClient()
        try:
            recommendation = await chat_client.generate_recommendation(chat_payload)
        finally:
            await chat_client.close()

        selected_garments = self._pick_selected_garments(garments, recommendation)

        image_client = ImageGeneratorClient()
        try:
            generation_payload = {
                "selfie_path": selfie.storage_path,
                "garment_paths": [garment.storage_path for garment in selected_garments],
                "instructions": recommendation.natural_text,
            }
            generation_result = await image_client.generate_outfit(generation_payload)
        finally:
            await image_client.close()

        return {
            "recommendation": recommendation,
            "selected_garments": selected_garments,
            "generation_result": generation_result,
        }
