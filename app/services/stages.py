"""Enumerations describing user onboarding stages."""

from enum import Enum


class OnboardingStage(str, Enum):
    """Finite states for guiding the user through the bot flow."""

    AWAITING_SELFIE = "awaiting_selfie"
    AWAITING_GARMENTS = "awaiting_garments"
    AWAITING_GARMENT_CATEGORY = "awaiting_garment_category"
    AWAITING_STYLE = "awaiting_style"
    READY = "ready"
