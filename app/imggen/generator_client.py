"""Async client for AITunnel image generation and editing."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI, BadRequestError
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
        except BadRequestError as exc:
            if "No valid image files provided" not in str(exc):
                raise
            prompt = self._build_fallback_prompt(payload)
            return await self._generate_with_prompt(prompt)
        finally:
            for file in image_files:
                file.close()

        return self._to_payload(result)

    def _build_fallback_prompt(self, payload: dict[str, Any]) -> str:
        """Compose a textual prompt when we cannot edit the selfie directly."""

        garment_list = ", ".join(payload.get("garment_labels", [])) or "подходящие вещи"
        base_instruction = payload.get("instructions", "").strip()
        extra = (
            "Сгенерируй портрет пользователя в полный рост в реалистичном стиле, "
            f"используя гардероб: {garment_list}. "
            "Сфокусируйся на дружелюбном, модном образе. Фон нейтральный."
        )
        if base_instruction:
            return f"{base_instruction}. {extra}"
        return extra

    async def _generate_with_prompt(self, prompt: str) -> dict[str, Any]:
        try:
            result = await self._client.images.generate(
                model=self._settings.aitunnel_image_model,
                prompt=prompt,
                size=self._settings.aitunnel_image_size,
                quality=self._settings.aitunnel_image_quality,
                response_format="b64_json",
            )
            return self._to_payload(result, fallback_prompt=prompt)
        except BadRequestError as exc:
            if "no_images_generated" in str(exc).lower():
                return {"image_base64": None, "image_url": None, "error": "no_images_generated", "prompt": prompt}
            raise

    def _to_payload(self, result, fallback_prompt: str | None = None) -> dict[str, Any]:
        primary = {}
        data_attr = getattr(result, "data", None)
        if isinstance(data_attr, list) and data_attr:
            primary = data_attr[0]
        else:
            primary = result
        image_base64 = getattr(primary, "b64_json", None)
        image_url = getattr(primary, "url", None)
        error_code = getattr(primary, "error", None)

        if image_base64 is None and isinstance(primary, dict):
            image_base64 = primary.get("b64_json")
        if image_url is None and isinstance(primary, dict):
            image_url = primary.get("url")
        if error_code is None and isinstance(primary, dict):
            error_code = primary.get("error")
        base_payload: dict[str, Any] = {
            "image_base64": image_base64,
            "image_url": image_url,
        }
        if fallback_prompt:
            base_payload["prompt"] = fallback_prompt
        if error_code:
            base_payload["error"] = error_code
        return base_payload

    async def ping(self) -> bool:
        """Return ``True`` when the service responds to a model listing call."""

        models = await self._client.models.list()
        return bool(models.data)

    async def close(self) -> None:
        """Close the underlying HTTP session."""

        await self._client.close()
