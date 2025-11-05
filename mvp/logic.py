"""High-level business logic for the MVP bot."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from mvp.api import AITunnelClient
from mvp.api.aitunnel_client import AITunnelRequestError
from mvp.config.settings import MVPSettings
from mvp.imggen import ImageGenerationService, OutfitPromptContext, PromptBuilder
from mvp.storage import UserProfile, UserStorage

logger = logging.getLogger(__name__)


class PreferenceExtractionError(RuntimeError):
    """Raised when ChatGPT response cannot be parsed."""


class OutfitPlanningError(RuntimeError):
    """Raised when the recommendation step fails."""


@dataclass(slots=True)
class OutfitResult:
    """Represents the final recommendation returned to the user."""

    summary: str
    recommended_paths: list[str]
    prompt: str
    image_path: str | None = None
    image_url: str | None = None


class StylistLogic:
    """Encapsulates preference parsing, outfit planning, and image generation."""

    def __init__(
        self,
        settings: MVPSettings,
        storage: UserStorage,
        client: AITunnelClient,
    ) -> None:
        self._settings = settings
        self._storage = storage
        self._client = client
        self._prompt_builder = PromptBuilder()
        self._image_service = ImageGenerationService(client, storage)

    async def update_preferences(self, profile: UserProfile, text: str) -> Mapping[str, Any]:
        """Analyse free-form text and update stored preferences."""

        messages = [
            {
                "role": "system",
                "content": (
                    "Ты — помощник-стилист. Классифицируй пользовательское описание стиля и верни JSON "
                    "формата {\"style_tags\": [], \"colors\": [], \"brand_refs\": [], \"notes\": \"\"}. "
                    "Строки выдавай на русском языке."
                ),
            },
            {
                "role": "user",
                "content": text,
            },
        ]
        try:
            response = await self._client.chat_completion(messages, response_format={"type": "json_object"})
        except AITunnelRequestError as exc:
            logger.error("Failed to fetch preferences from AITunnel: %s", exc)
            raise PreferenceExtractionError(
                "Не удалось получить ответ от сервиса стиля. Попробуйте позже или уточните данные.",
            ) from exc
        content = self._first_choice_content(response, PreferenceExtractionError)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise PreferenceExtractionError("Не удалось распознать предпочтения.") from exc

        await self._storage.update_preferences(profile, parsed)
        return parsed

    async def plan_outfit(self, profile: UserProfile, extra_context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        """Call the chat model to select outfit items and generate verbal description."""

        wardrobe_payload = profile.wardrobe
        preferences = profile.preferences
        payload = {
            "wardrobe": wardrobe_payload,
            "preferences": preferences,
            "daily_context": {**profile.daily_context, **(extra_context or {})},
        }
        messages = [
            {
                "role": "system",
                "content": (
                    "Ты — AI-стилист. Подбирай образ только из файлов wardrobe пользователя. "
                    "Каждый элемент списка wardrobe представляет путь к локальному изображению. "
                    "Ответ строго в JSON: {\"recommended_items\": [{\"category\": \"top\", \"path\": \"...\", "
                    "\"label\": \"...\"}], \"summary_text\": \"...\", \"prompt_text\": \"...\"}. "
                    "Поле path должно быть точной строкой из входного словаря wardrobe. "
                    "Не добавляй Markdown и комментарии, не придумывай новых вещей."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False),
            },
        ]
        try:
            response = await self._client.chat_completion(messages, response_format={"type": "json_object"})
        except AITunnelRequestError as exc:
            logger.error("Failed to build outfit via ChatGPT: %s", exc)
            raise OutfitPlanningError(
                "Сервис рекомендаций временно недоступен. Попробуйте повторить запрос позже.",
            ) from exc
        content = self._first_choice_content(response, OutfitPlanningError)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise OutfitPlanningError("Не удалось получить рекомендации от модели.") from exc
        return parsed

    async def generate_outfit(
        self,
        profile: UserProfile,
        *,
        extra_context: Mapping[str, Any] | None = None,
    ) -> OutfitResult:
        """Produce the final outfit text + image result."""

        if not profile.selfie_path:
            raise OutfitPlanningError("Сначала загрузите селфи.")

        if not any(profile.wardrobe.values()):
            raise OutfitPlanningError("Гардероб пуст. Добавьте несколько вещей.")

        recommendation = await self.plan_outfit(profile, extra_context=extra_context)
        items = recommendation.get("recommended_items", []) or []
        recommended = self._select_paths(profile, items)
        if not recommended:
            # fallback: at least take first items from each category
            recommended = self._fallback_paths(profile)

        prompt_context = OutfitPromptContext(
            description=recommendation.get("prompt_text", ""),
            style=profile.preferences.get("notes"),
            occasion=(extra_context or {}).get("occasion") or profile.daily_context.get("occasion"),
            weather=(extra_context or {}).get("weather") or profile.daily_context.get("weather"),
        )

        garment_details = self._build_garment_details(profile, recommended, items)
        prompt = self._prompt_builder.build(
            garment_details,
            prompt_context,
            selfie_filename=Path(profile.selfie_path).name,
        )

        try:
            image_result = await self._image_service.generate(
                profile.user_id,
                prompt,
                selfie_path=Path(profile.selfie_path),
                garments=garment_details,
                options={"size": "1024x1536", "quality": "high"},
            )
        except AITunnelRequestError as exc:
            logger.error("Failed to generate image via AITunnel Gemini: %s", exc)
            raise OutfitPlanningError(
                "Не удалось сгенерировать изображение. Попробуйте повторить запрос чуть позже.",
            ) from exc

        return OutfitResult(
            summary=recommendation.get("summary_text", "Готов образ на сегодня!"),
            recommended_paths=list(recommended),
            prompt=prompt,
            image_path=image_result.get("image_path"),
            image_url=image_result.get("image_url"),
        )

    def _select_paths(self, profile: UserProfile, recommended_items: Sequence[Mapping[str, Any]]) -> list[str]:
        resolved: list[str] = []
        for item in recommended_items:
            path = item.get("path")
            category = item.get("category")
            if path and Path(path).exists():
                resolved.append(path)
                continue
            if category and category in profile.wardrobe and profile.wardrobe[category]:
                resolved.append(profile.wardrobe[category][0])
        return resolved

    def _fallback_paths(self, profile: UserProfile) -> list[str]:
        fallback: list[str] = []
        for items in profile.wardrobe.values():
            if items:
                fallback.append(items[0])
        return fallback[:3]

    def _build_garment_details(
        self,
        profile: UserProfile,
        selected_paths: Sequence[str],
        recommendation_items: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, str]]:
        """Enrich selected garment paths with metadata for prompt construction."""

        by_path = {str(item.get("path")): item for item in recommendation_items if isinstance(item, Mapping)}
        details: list[dict[str, str]] = []
        for path in selected_paths:
            category = self._find_category_for_path(profile, path)
            label = Path(path).stem
            rec_item = by_path.get(path)
            if rec_item:
                label = rec_item.get("label") or rec_item.get("name") or label
            details.append(
                {
                    "path": path,
                    "category": category or "неизвестно",
                    "label": label,
                    "filename": Path(path).name,
                },
            )
        return details

    def _find_category_for_path(self, profile: UserProfile, path: str) -> str | None:
        for category, paths in profile.wardrobe.items():
            if path in paths:
                return category
        return None

    @staticmethod
    def _first_choice_content(response: Mapping[str, Any], error_cls: type[Exception]) -> str:
        choices = response.get("choices", [])
        if not choices:
            raise error_cls("Модель не вернула ответ.")
        return choices[0]["message"]["content"]  # type: ignore[index]
