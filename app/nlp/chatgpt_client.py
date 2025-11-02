"""Client for dialog generation via the configured LLM provider."""

from __future__ import annotations

import json

import httpx
from pydantic import BaseModel

from app.config.settings import get_settings


class RecommendationResponse(BaseModel):
    """Structured response returned by the dialog model."""

    suggested_outfit: list[dict[str, object]]
    natural_text: str
    reasons: list[str]
    missing_items: list[str]


class ChatGPTClient:
    """Thin HTTP client that communicates with the aitunnel proxy."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.aitunnel_api_key:
            raise RuntimeError("AITunnel API key is not configured.")
        self._client = httpx.AsyncClient(
            base_url=settings.aitunnel_base_url,
            headers={"Authorization": f"Bearer {settings.aitunnel_api_key}"},
            timeout=30.0,
        )
        self._health_path = settings.aitunnel_health_path

    async def generate_recommendation(self, payload: dict) -> RecommendationResponse:
        """Send a recommendation prompt to the chat model."""

        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        if "choices" in data and data["choices"]:
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        else:
            parsed = data
        return RecommendationResponse.model_validate(parsed)

    async def ping(self) -> bool:
        """Return ``True`` if the upstream service responds to a health check."""

        response = await self._client.get(self._health_path)
        response.raise_for_status()
        return response.is_success

    async def close(self) -> None:
        """Release HTTP resources."""

        await self._client.aclose()
