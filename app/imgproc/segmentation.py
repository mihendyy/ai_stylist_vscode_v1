"""Image segmentation helpers."""

from __future__ import annotations


class SegmentationService:
    """Placeholder interface for SAM/Detectron2 models."""

    def segment(self, image_bytes: bytes) -> bytes:
        """Return raw mask bytes for the given image."""

        raise NotImplementedError("Segmentation is not wired yet.")
