"""Image classification stubs for wardrobe items."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class GarmentAttributes:
    """Attributes collected from the garment classifier."""

    label: str
    subclass: str | None
    color_hex: str | None
    pattern: str | None
    material: str | None
    fit: str | None


class GarmentClassifier:
    """Placeholder for a CV model integration."""

    def classify(self, image_bytes: bytes) -> GarmentAttributes:
        """
        Analyse an image and return garment attributes.

        Implementing the actual ML pipeline is outside of this commit scope.
        """

        raise NotImplementedError("Garment classification is not implemented yet.")
