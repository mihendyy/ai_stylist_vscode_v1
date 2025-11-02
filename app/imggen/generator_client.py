"""Async client for AITunnel image generation and editing."""

from __future__ import annotations

import base64
from io import BytesIO

from openai import AsyncOpenAI

from app.config.settings import get_settings


class ImageGeneratorClient:
    """Handles outfit image generation using the AITunnel proxy."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.aitunnel_api_key:
            raise RuntimeError("AITunnel API key is not configured.")

        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.aitunnel_api_key,
            base_url=settings.aitunnel_base_url.rstrip("/"),
        )

    async def generate_outfit(self, payload: dict) -> dict:
        """Send outfit images to the multimodal model and return base64 response."""

        selfie_bytes = base64.b64decode(payload["selfie_image"])
        garment_files: list[BytesIO] = []

        selfie_file = BytesIO(selfie_bytes)
        selfie_file.name = "selfie.png"

        for index, garment in enumerate(payload.get("garment_images", []), start=1):
            garment_file = BytesIO(base64.b64decode(garment["image"]))
            garment_file.name = f"garment_{index}.png"
            garment_files.append(garment_file)

        images = [selfie_file, *garment_files]

        result = await self._client.images.edit(
            model=self._settings.aitunnel_image_model,
            image=images,  # type: ignore[arg-type]
            prompt=payload["instructions"],
            size=self._settings.aitunnel_image_size,
            quality=self._settings.aitunnel_image_quality,
            moderation=self._settings.aitunnel_image_moderation,
            response_format="b64_json",
        )

        return {
            "image_base64": result.data[0].b64_json,
        }

    async def ping(self) -> bool:
        """Return ``True`` when the service responds to a model listing call."""

        models = await self._client.models.list()
        return bool(models.data)

    async def close(self) -> None:
        """Close the underlying HTTP session."""

        await self._client.close()
