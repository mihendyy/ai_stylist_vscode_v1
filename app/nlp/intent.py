"""Intent extraction primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(slots=True)
class IntentExtractionResult:
    """Represents a parsed user intent."""

    intent: str
    confidence: float
    entities: dict[str, str]


class IntentClassifier:
    """Simple keyword-based classifier used until the NLP model is integrated."""

    def __init__(self, keywords: dict[str, Iterable[str]] | None = None) -> None:
        self._keywords = keywords or {
            "add_garment": {"добавь", "загрузи", "добавить"},
            "today_outfit": {"что надеть", "образ", "лук"},
            "feedback_positive": {"нравится", "класс", "🔥"},
            "feedback_negative": {"не нравится", "ужас", "👎"},
        }

    def parse_message(self, message: str) -> IntentExtractionResult:
        """Return a naive classification result based on keyword matching."""

        lower = message.lower()
        for intent, synonyms in self._keywords.items():
            if any(keyword in lower for keyword in synonyms):
                return IntentExtractionResult(intent=intent, confidence=0.6, entities={})
        return IntentExtractionResult(intent="unknown", confidence=0.1, entities={})
