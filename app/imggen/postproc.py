"""Post-processing utilities for generated images."""

from __future__ import annotations


class ImagePostProcessor:
    """Applies quality checks and minor adjustments to generated images."""

    def ensure_identity_match(self, original_embedding: list[float], generated_embedding: list[float]) -> bool:
        """Return True when embeddings similarity exceeds the threshold."""

        raise NotImplementedError("Identity verification is not yet implemented.")

    def enhance_colors(self, image_bytes: bytes) -> bytes:
        """Placeholder for colour correction pipeline."""

        raise NotImplementedError("Post-processing is not implemented yet.")
