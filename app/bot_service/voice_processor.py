"""Voice-to-text processing utilities."""

from __future__ import annotations

import logging
from typing import Optional

from aiogram.types import Message

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class VoiceProcessor:
    """High-level wrapper that delegates voice transcription to Whisper or similar STT."""

    async def transcribe_voice(self, message: Message) -> Optional[str]:
        """
        Download a voice message and send it to the STT provider.

        The actual API integration is intentionally left unimplemented to avoid leaking
        credentials in the repository. The method currently returns ``None`` so that we
        never mislead a user with fake content.
        """

        settings = get_settings()
        if not settings.aitunnel_api_key:
            logger.warning("AITunnel API key is not configured; skipping transcription.")
            return None

        file = await message.bot.get_file(message.voice.file_id)
        voice_bytes = await message.bot.download_file(file.file_path)
        # TODO: send ``voice_bytes`` to the configured Whisper endpoint.
        voice_bytes.close()
        return None
