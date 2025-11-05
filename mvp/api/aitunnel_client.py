"""Async wrapper around the AITunnel API endpoints."""

from __future__ import annotations

import base64
import binascii
import json
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import httpx
import logging
from openai import AsyncOpenAI, BadRequestError
from PIL import Image, UnidentifiedImageError

from mvp.config.settings import MVPSettings


class AITunnelRequestError(RuntimeError):
    """Raised when AITunnel responds with an error status code."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


logger = logging.getLogger(__name__)


class AITunnelClient:
    """Provides helper methods for ChatGPT, Whisper, and Gemini calls."""

    def __init__(self, settings: MVPSettings) -> None:
        base_url = settings.aitunnel_base_url.rstrip("/")
        self._settings = settings
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=settings.request_timeout,
            headers={
                "Authorization": f"Bearer {settings.aitunnel_api_key}",
            },
        )
        self._openai = AsyncOpenAI(
            api_key=settings.aitunnel_api_key,
            base_url=base_url,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""

        await self._client.aclose()
        await self._openai.close()

    async def _request_json(
        self,
        method: str,
        endpoint: str,
        *,
        json_body: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        files: Iterable[tuple[str, tuple[str, bytes, str]]] | None = None,
    ) -> dict[str, Any]:
        try:
            response = await self._client.request(
                method,
                endpoint,
                json=json_body,
                data=data,
                files=files,
            )
            response.raise_for_status()
            if not response.content:
                return {}
            return response.json()
        except httpx.TimeoutException as exc:  # pragma: no cover - network safeguard
            raise AITunnelRequestError("Превышено время ожидания ответа от AITunnel.") from exc
        except httpx.HTTPStatusError as exc:
            raise AITunnelRequestError(
                f"AITunnel вернул ошибку {exc.response.status_code}: {exc.response.text}",
                status_code=exc.response.status_code,
            ) from exc

    async def chat_completion(self, messages: Sequence[Mapping[str, Any]], **kwargs: Any) -> dict[str, Any]:
        """Call the OpenAI-compatible chat completions endpoint."""

        payload = {
            "model": self._settings.aitunnel_chat_model,
            "messages": list(messages),
        }
        payload.update(kwargs)
        return await self._request_json("POST", "/chat/completions", json_body=payload)

    async def transcribe_audio(self, audio_bytes: bytes, filename: str) -> str:
        """Send audio bytes to Whisper STT and return the transcript."""

        files = [
            ("file", (filename, audio_bytes, "audio/ogg")),
        ]
        data = {
            "model": self._settings.aitunnel_stt_model,
            "response_format": "json",
        }
        result = await self._request_json(
            "POST",
            "/audio/transcriptions",
            data=data,
            files=files,
        )
        return result.get("text", "")

    async def generate_image(
        self,
        prompt: str,
        *,
        selfie_path: Path,
        garments: Sequence[Mapping[str, str]],
        options: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate an edited selfie using the OpenAI-compatible images.edit endpoint."""

        image_files: list[BytesIO] = []
        try:
            if selfie_path.exists():
                image_files.append(self._image_as_png(selfie_path, "selfie"))
            else:
                raise FileNotFoundError(f"Основное изображение не найдено: {selfie_path}")

            for index, garment in enumerate(garments, start=1):
                path = Path(garment.get("path", ""))
                if not path.exists():
                    logger.warning("Garment path %s does not exist; skipping.", path)
                    continue
                image_files.append(self._image_as_png(path, f"garment_{index}"))

            kwargs: dict[str, Any] = {
                "model": self._settings.aitunnel_image_model,
                "image": image_files,
                "prompt": prompt,
            }
            if options:
                kwargs.update(options)

            try:
                result = await self._openai.images.edit(**kwargs)
            except BadRequestError as exc:
                fallback = self._fallback_image_model(kwargs["model"], str(exc))
                if fallback:
                    logger.warning("Model %s unavailable, retrying with %s", kwargs["model"], fallback)
                    kwargs["model"] = fallback
                    result = await self._openai.images.edit(**kwargs)
                else:
                    raise
            return self._normalise_image_response(result)
        finally:
            for file in image_files:
                file.close()

    def _image_as_png(self, source_path: Path, name_prefix: str) -> BytesIO:
        try:
            with Image.open(source_path) as img:
                img = img.convert("RGBA")
                buffer = BytesIO()
                img.save(buffer, format="PNG")
        except UnidentifiedImageError as exc:
            raise ValueError(f"Файл {source_path} не является поддерживаемым изображением.") from exc
        buffer.seek(0)
        buffer.name = f"{name_prefix}.png"
        return buffer

    def _normalise_image_response(self, result: Any) -> dict[str, Any]:
        data_attr = getattr(result, "data", None)
        payload: dict[str, Any] = {}
        if isinstance(data_attr, list) and data_attr:
            primary = data_attr[0]
            image_base64 = getattr(primary, "b64_json", None)
            image_url = getattr(primary, "url", None)
            if image_base64 is None and isinstance(primary, Mapping):
                image_base64 = primary.get("b64_json")
                image_url = image_url or primary.get("url")
            payload["image_base64"] = image_base64
            payload["image_url"] = image_url
        else:
            payload["raw"] = result
        return payload

    def _fallback_image_model(self, current: str, error_message: str) -> str | None:
        if current.endswith("-preview"):
            return current.replace("-preview", "")
        if "gemini-2.5-flash-image" in current and "не найдена" in error_message.lower():
            return "gpt-image-1"
        return None

    @staticmethod
    def image_payload_to_result(payload: Mapping[str, Any]) -> tuple[bytes | None, str | None]:
        """Extract base64 image content or URL from the chat completions response."""

        choices = payload.get("choices") or []
        if not choices:
            logger.warning("AITunnel image response has no choices: %s", payload)
            return None, None
        message = choices[0].get("message") or {}
        image_url = None

        images = message.get("images") or []
        if images:
            image_entry = images[0] or {}
            if isinstance(image_entry, Mapping):
                image_info = image_entry.get("image_url") or {}
                if isinstance(image_info, Mapping):
                    image_url = image_info.get("url")

        content = message.get("content")
        if image_url is None and isinstance(content, str) and content.startswith("data:"):
            image_url = content
        elif image_url is None and isinstance(content, list):
            for part in content:
                if (
                    isinstance(part, Mapping)
                    and part.get("type") == "image_url"
                    and isinstance(part.get("image_url"), Mapping)
                ):
                    image_url = part["image_url"].get("url")
                    if image_url:
                        break

        if not image_url:
            logger.warning("AITunnel image response contains no image_url field: %s", message)
            return None, None

        if image_url.startswith("data:") and "," in image_url:
            _, encoded = image_url.split(",", 1)
            try:
                return base64.b64decode(encoded), image_url
            except (ValueError, binascii.Error):  # type: ignore[name-defined]
                return None, image_url

        return None, image_url
