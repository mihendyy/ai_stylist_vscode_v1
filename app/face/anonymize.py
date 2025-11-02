"""Utilities for anonymising face data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AnonymisedFace:
    """Result of anonymisation process."""

    blurred_image: bytes
    metadata_removed: bool


class FaceAnonymizer:
    """Provides deterministic anonymisation for user photos."""

    def anonymise(self, image_bytes: bytes) -> AnonymisedFace:
        """Return an anonymised version of the original image."""

        raise NotImplementedError("Face anonymisation not implemented yet.")
