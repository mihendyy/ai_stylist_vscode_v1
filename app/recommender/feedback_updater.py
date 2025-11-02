"""Feedback-driven model updates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class FeedbackEvent:
    """Normalised feedback payload."""

    user_id: str
    outfit_reference: str
    is_positive: bool
    reason: str | None = None


class FeedbackUpdater:
    """Applies online learning updates based on user feedback."""

    def apply(self, feedback: FeedbackEvent) -> None:
        """Schedule feedback processing."""

        _ = feedback  # future hook for worker integration
        # TODO: push event to task queue
