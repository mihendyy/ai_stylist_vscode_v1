"""Simple finite state machine that tracks onboarding progress."""

from __future__ import annotations

from enum import Enum

from mvp.storage import UserProfile, UserStorage


class ConversationState(str, Enum):
    """Conversation stages for the MVP flow."""

    AWAITING_SELFIE = "awaiting_selfie"
    AWAITING_GARMENT = "awaiting_garment"
    AWAITING_CATEGORY = "awaiting_category"
    AWAITING_PREFERENCES = "awaiting_preferences"
    READY = "ready"
    AWAITING_DAILY_CONTEXT = "awaiting_daily_context"


class StateMachine:
    """Wrapper that keeps the profile state in sync with storage."""

    def __init__(self, storage: UserStorage) -> None:
        self._storage = storage

    def current(self, profile: UserProfile) -> ConversationState:
        """Return the current conversation state."""

        try:
            return ConversationState(profile.stage)
        except ValueError:
            return ConversationState.AWAITING_SELFIE

    async def set_state(self, profile: UserProfile, state: ConversationState) -> None:
        """Persist the new state."""

        await self._storage.set_stage(profile, state.value)
