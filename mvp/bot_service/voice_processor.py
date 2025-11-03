"""Voice message transcription helpers."""

from __future__ import annotations

import logging
from pathlib import Path

from aiogram.types import Message

from mvp.api import AITunnelClient

logger = logging.getLogger(__name__)


class VoiceProcessor:
    """Downloads Telegram voice notes and forwards them to Whisper."""

    def __init__(self, client: AITunnelClient) -> None:
        self._client = client

    async def transcribe(self, message: Message) -> str | None:
        """Return recognised text or ``None`` if transcription fails."""

        if not message.voice:
            return None

        file_info = await message.bot.get_file(message.voice.file_id)
        file_stream = await message.bot.download_file(file_info.file_path)
        audio_bytes = file_stream.read()
        file_stream.close()

        filename = Path(file_info.file_path or "voice.ogg").name
        try:
            transcript = await self._client.transcribe_audio(audio_bytes, filename)
            return transcript or None
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to transcribe voice message")
            return None
