"""Gemini-based image generation service."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Mapping, Sequence

from mvp.api.aitunnel_client import AITunnelClient
from mvp.storage.repository import UserStorage

logger = logging.getLogger(__name__)


class ImageGenerationService:
    """Coordinates prompt submission and storage of generated images."""

    def __init__(self, client: AITunnelClient, storage: UserStorage) -> None:
        self._client = client
        self._storage = storage

    async def generate(
        self,
        user_id: str,
        prompt: str,
        selfie_path: Path,
        garments: Sequence[Mapping[str, str]],
        *,
        options: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        """
        Generate an outfit image and return metadata with path or URL.

        Returns dictionary containing ``prompt``, ``image_path`` or ``image_url``.
        """

        result = await self._client.generate_image(
            prompt,
            selfie_path=selfie_path,
            garments=garments,
            options=options,
        )
        image_bytes, data_url = AITunnelClient.image_payload_to_result(result)
        if image_bytes:
            generated_dir = self._storage.get_generated_dir(user_id)
            output_path = generated_dir / f"outfit_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jpg"
            await asyncio.to_thread(output_path.write_bytes, image_bytes)
            return {"prompt": prompt, "image_path": str(output_path)}

        image_url = data_url or ""
        logger.warning("AITunnel image response did not include binary data; returning data URL.")
        return {
            "prompt": prompt,
            "image_url": image_url,
        }
