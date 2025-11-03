"""Async wrapper around the AITunnel API endpoints."""

from __future__ import annotations

import base64
import binascii
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import httpx
import logging

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

    async def close(self) -> None:
        """Close the underlying HTTP client."""

        await self._client.aclose()

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
        image_paths: Sequence[Path],
        *,
        options: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Trigger image generation via the chat completions endpoint with image modality.

        ``image_paths`` should contain local file paths (selfie and garments) that will be
        embedded into the request as base64 data URLs.
        """

        content_parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for path in image_paths:
            if not path.exists():
                continue
            suffix = path.suffix.lower()
            mime = "image/png" if suffix == ".png" else "image/jpeg"
            encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
            data_url = f"data:{mime};base64,{encoded}"
            content_parts.append(
                {
                    "type": "image_url",
                    "image_url": {"url": data_url, "detail": "high"},
                },
            )

        if options:
            options_text = ", ".join(f"{key}={value}" for key, value in options.items())
            content_parts.append({"type": "text", "text": f"Параметры генерации: {options_text}"})

        payload: dict[str, Any] = {
            "model": self._settings.aitunnel_image_model,
            "messages": [
                {
                    "role": "user",
                    "content": content_parts,
                },
            ],
            "modalities": ["image", "text"],
        }

        return await self._request_json(
            "POST",
            "/chat/completions",
            json_body=payload,
        )

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
