"""Image normalisation helpers."""

from __future__ import annotations


class ImageNormalizer:
    """Ensures consistent orientation and aspect ratio."""

    def normalize(self, image_bytes: bytes) -> bytes:
        """Return processed image bytes ready for downstream services."""

        raise NotImplementedError("Image normalisation not implemented yet.")
