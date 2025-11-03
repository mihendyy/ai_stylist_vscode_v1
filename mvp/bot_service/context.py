"""Shared dependencies passed into handler setup functions."""

from __future__ import annotations

from dataclasses import dataclass

from mvp.logic import StylistLogic
from mvp.storage import UserStorage
from mvp.bot_service.state_machine import StateMachine


@dataclass(slots=True)
class BotContext:
    """Container for objects shared across handlers."""

    storage: UserStorage
    logic: StylistLogic
    state_machine: StateMachine
