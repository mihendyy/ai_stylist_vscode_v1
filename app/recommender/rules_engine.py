"""Business rules for outfit generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(slots=True)
class OutfitRule:
    """Represents a single business rule constraint."""

    name: str
    description: str

    def is_satisfied(self, context: dict) -> bool:
        """Evaluate the rule for the provided context."""

        raise NotImplementedError


class RulesEngine:
    """Evaluates a collection of outfit rules."""

    def __init__(self, rules: Iterable[OutfitRule]) -> None:
        self._rules = list(rules)

    def evaluate(self, context: dict) -> list[str]:
        """Return names of rules that failed validation."""

        failed: list[str] = []
        for rule in self._rules:
            if not rule.is_satisfied(context):
                failed.append(rule.name)
        return failed
