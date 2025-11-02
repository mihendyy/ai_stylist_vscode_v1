"""Attribute extraction helpers for garments."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AttributeConfidence:
    """Stores attribute value with confidence scores."""

    value: str | None
    confidence: float


@dataclass(slots=True)
class GarmentAttributeBundle:
    """Aggregate of garment attributes used by the recommender."""

    color: AttributeConfidence
    pattern: AttributeConfidence
    material: AttributeConfidence
    length: AttributeConfidence
    fit: AttributeConfidence


class AttributeExtractor:
    """Transformer that enriches classifier output with additional metadata."""

    def extract(self, image_bytes: bytes) -> GarmentAttributeBundle:
        """Placeholder implementation until the CV pipeline is ready."""

        raise NotImplementedError("Attribute extraction is not implemented.")
