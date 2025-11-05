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
        garments: Sequence[dict[str, str]],
        prompt_context: OutfitPromptContext,
        *,
        selfie_filename: str,
        extra_instructions: Iterable[str] | None = None,
    ) -> str:
        """Return a natural-language instruction for editing the selfie with wardrobe items."""

        garment_lines: list[str] = []
        for index, garment in enumerate(garments, start=1):
            label = garment.get("label") or garment.get("filename") or f"предмет {index}"
            category = garment.get("category")
            file_name = garment.get("filename") or "изображение"
            descriptor = label if not category else f"{label} ({category})"
            garment_lines.append(f"{index}) {descriptor} — файл {file_name}.")

        garments_text = (
            "Используй прилагаемые фотографии вещей без изменений:\n"
            + "\n".join(garment_lines)
        ) if garment_lines else "Используй доступные фотографии гардероба."

        summary = prompt_context.summary()
        extras = " ".join(extra_instructions or [])
        instructions = (
            "Ты получишь селфи пользователя и отдельные фотографии вещей из его гардероба. "
            f"Основное изображение: файл {selfie_filename}. "
            "Твоя задача — отредактировать селфи, надев пользователя ровно в эти вещи. "
            "Не придумывай новые элементы, не меняй цвета и фасоны, сохрани лицо и особенности фигуры."
        )
        return " ".join(
            part
            for part in [
                instructions,
                garments_text,
                summary,
                "Сцена должна быть реалистичной, с естественным светом и уверенной позой.",
                extras,
            ]
            if part
        ).strip()
