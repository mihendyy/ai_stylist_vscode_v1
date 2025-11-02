"""Async client for AITunnel image generation and editing."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from openai import AsyncOpenAI
from PIL import Image

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

    def _image_as_png(self, source_path: Path, name_prefix: str) -> BytesIO:
        """Convert arbitrary image to PNG bytes since edit API requires PNG input."""

        with Image.open(source_path) as img:
            img = img.convert("RGBA")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
        buffer.name = f"{name_prefix}.png"
        return buffer

    async def generate_outfit(self, payload: dict) -> dict:
        """Send outfit images to the multimodal model and return base64 response."""

        image_files: list[BytesIO] = []
        try:
            selfie_path = Path(payload["selfie_path"]).expanduser()
            image_files.append(self._image_as_png(selfie_path, "selfie"))

            for index, garment_path_str in enumerate(payload.get("garment_paths", []), start=1):
                garment_path = Path(garment_path_str).expanduser()
                image_files.append(self._image_as_png(garment_path, f"garment_{index}"))

            result = await self._client.images.edit(
                model=self._settings.aitunnel_image_model,
                image=image_files,  # type: ignore[arg-type]
                prompt=payload["instructions"],
                size=self._settings.aitunnel_image_size,
                quality=self._settings.aitunnel_image_quality,
                response_format="b64_json",
            )
        finally:
            for file in image_files:
                file.close()

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
