"""Client for dialog generation via the configured LLM provider."""

from __future__ import annotations

import json

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config.settings import get_settings


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
        parsed = json.loads(content)
        return RecommendationResponse.model_validate(parsed)

    async def ping(self) -> bool:
        """Return ``True`` if the upstream service responds to a model listing call."""

        models = await self._client.models.list()
        return bool(models.data)

    async def close(self) -> None:
        """Release HTTP resources."""

        await self._client.close()
