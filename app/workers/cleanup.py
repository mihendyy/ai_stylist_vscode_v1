"""Cleanup tasks for expired media."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.storage.backend import LocalStorage


def remove_expired_media(storage: LocalStorage, ttl_days: int) -> int:
    """
    Iterate through storage and delete expired items.

    Returns the number of deleted files. Actual file discovery is not implemented yet.
    """

    _ = storage, ttl_days, datetime.utcnow(), timedelta(days=ttl_days)
    return 0
