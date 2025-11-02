"""Dominant colour extraction utilities."""

from __future__ import annotations

from collections import Counter
from typing import Iterable


class ColorExtractor:
    """Naive RGB histogram-based colour detector."""

    def extract_palette(self, pixels: Iterable[tuple[int, int, int]], top_n: int = 3) -> list[str]:
        """Return hex codes for most common colours."""

        counter = Counter(pixels)
        dominant = counter.most_common(top_n)
        return [f"#{r:02x}{g:02x}{b:02x}" for (r, g, b), _ in dominant]
