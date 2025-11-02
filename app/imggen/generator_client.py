"""Async client for the image generation provider."""

from __future__ import annotations

import httpx

from app.config.settings import get_settings


class ImageGeneratorClient:
    """Handles requests to the Fal.ai API."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.kie_ai_api_key:
            raise RuntimeError("KIE AI API key is not configured.")

        self._client = httpx.AsyncClient(
            base_url=settings.kie_base_url,
            headers={"Authorization": f"Key {settings.kie_ai_api_key}"},
            timeout=60.0,
        )

        self._health_path = settings.kie_health_path
        self._nano_banana_endpoint = "/nano-banana/v1/edit"

    async def generate_outfit(self, payload: dict) -> dict:
        """Send request to the Nano Banana edit endpoint and return JSON response."""

        response = await self._client.post(self._nano_banana_endpoint, json=payload)
        response.raise_for_status()
        return response.json()

    async def ping(self) -> bool:
        """Return ``True`` when the service responds to a health check."""

        response = await self._client.get(self._health_path)
        response.raise_for_status()
        return response.is_success

    async def close(self) -> None:
        """Close the underlying HTTP session."""

        await self._client.aclose()
