"""Prompt builder for the image generation service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SceneMetadata:
    """Subset of the scene JSON required by the generator."""

    scene_id: str
    user_id: str
    intent: str
    occasion: str | None = None
    weather_context: dict[str, Any] | None = None
    inspiration: list[str] = field(default_factory=list)


class PromptBuilder:
    """Compose generator payloads from structured data."""

    def build(self, base_payload: dict[str, Any], metadata: SceneMetadata) -> dict[str, Any]:
        """Return a payload ready for the Fal.ai API."""

        payload = {
            **base_payload,
            "meta": {
                **base_payload.get("meta", {}),
                "scene_id": metadata.scene_id,
                "user_id": metadata.user_id,
                "intent": metadata.intent,
                "occasion": metadata.occasion,
                "weather_context": metadata.weather_context,
                "inspiration": metadata.inspiration,
            },
        }
        return payload
