"""Prompt construction helpers for the image generation step."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(slots=True)
class OutfitPromptContext:
    """Structured information used to build the visual prompt."""

    description: str
    style: str | None = None
    occasion: str | None = None
    weather: str | None = None
    mood: str | None = None

    def summary(self) -> str:
        parts = [self.description]
        if self.style:
            parts.append(f"Стиль: {self.style}.")
        if self.occasion:
            parts.append(f"Повод: {self.occasion}.")
        if self.weather:
            parts.append(f"Условия: {self.weather}.")
        if self.mood:
            parts.append(f"Настроение: {self.mood}.")
        return " ".join(parts).strip()


class PromptBuilder:
    """Builds textual prompts for Gemini based on chat output."""

    def build(
        self,
        garment_labels: Sequence[str],
        prompt_context: OutfitPromptContext,
        extra_instructions: Iterable[str] | None = None,
    ) -> str:
        """Return a natural-language prompt describing the desired outfit."""

        garments = ", ".join(garment_labels) if garment_labels else "подходящие вещи из гардероба"
        base = (
            f"Пусть человек на фото будет одет в {garments}. "
            f"{prompt_context.summary()} "
            "Задай естественную позу и реалистичный свет. Сохрани внешность пользователя."
        )
        extras = " ".join(extra_instructions or [])
        return f"{base} {extras}".strip()
