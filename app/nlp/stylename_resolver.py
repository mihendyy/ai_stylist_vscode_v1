"""Normalise free-form style references into canonical tags."""

from __future__ import annotations

from typing import Dict


class StyleNameResolver:
    """Maps celebrity/style references to internal tags."""

    def __init__(self) -> None:
        self._aliases: Dict[str, str] = {
            "тимоте шаламе": "celebrity_timothee_chalamet",
            "timothée chalamet": "celebrity_timothee_chalamet",
            "street": "style_street",
            "casual": "style_casual",
            "smart": "style_smart",
            "office": "occasion_office",
            "date": "occasion_date",
        }

    def resolve(self, raw_value: str) -> str:
        """Return a canonical tag or the original lower-cased value."""

        key = raw_value.strip().lower()
        return self._aliases.get(key, key)
