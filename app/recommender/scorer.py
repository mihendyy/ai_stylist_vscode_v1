"""Outfit scoring utilities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class OutfitCandidate:
    """Combination of garments proposed to the user."""

    items: list[str]
    score: float


class OutfitScorer:
    """Ranks outfit candidates based on heuristic scoring."""

    def score(self, candidate: OutfitCandidate, context: dict) -> float:
        """Return a numeric score where higher is better."""

        _ = context  # reserved for future use
        return candidate.score
