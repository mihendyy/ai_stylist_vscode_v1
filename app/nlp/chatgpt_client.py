"""Client for dialog generation via the configured LLM provider."""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class RecommendationResponse(BaseModel):
    """Structured response returned by the dialog model."""

    suggested_outfit: list[dict[str, object]]
    natural_text: str
    reasons: list[str]
    missing_items: list[str]


class ChatGPTClient:
    """Thin client that communicates with the AITunnel OpenAI-compatible proxy."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.aitunnel_api_key:
            raise RuntimeError("AITunnel API key is not configured.")

        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.aitunnel_api_key,
            base_url=settings.aitunnel_base_url.rstrip("/"),
        )

    async def generate_recommendation(self, payload: dict) -> RecommendationResponse:
        """Send a recommendation prompt to the chat model."""

        response = await self._client.chat.completions.create(
            model=self._settings.aitunnel_chat_model,
            messages=payload["messages"],
            max_tokens=payload.get("max_tokens", 1200),
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse recommendation JSON: %s", content)
            parsed = {"natural_text": content}
        return self._coerce_response(parsed)

    async def ping(self) -> bool:
        """Return ``True`` if the upstream service responds to a model listing call."""

        models = await self._client.models.list()
        return bool(models.data)

    async def close(self) -> None:
        """Release HTTP resources."""

        await self._client.close()

    def _coerce_response(self, payload: Any) -> RecommendationResponse:
        """Attempt to validate provider response and fall back to safe defaults."""

        if isinstance(payload, str):
            payload = {"natural_text": payload}

        if not isinstance(payload, dict):
            payload = {}

        def _as_list(value: Any) -> list[str]:
            if isinstance(value, list):
                return [str(item) for item in value]
            if isinstance(value, str) and value:
                return [value]
            return []

        default_payload = {
            "suggested_outfit": payload.get("suggested_outfit") or [],
            "natural_text": payload.get("natural_text")
            or "Я пока не смог подобрать образ из-за недостатка данных. Пожалуйста, уточните стиль или добавьте больше вещей.",
            "reasons": _as_list(payload.get("reasons")),
            "missing_items": _as_list(payload.get("missing_items")),
        }

        try:
            return RecommendationResponse.model_validate(default_payload)
        except ValidationError as exc:
            logger.error("Invalid recommendation payload after coercion: %s", payload)
            raise RuntimeError(
                "Модель рекомендаций вернула некорректный формат ответа.",
            ) from exc
