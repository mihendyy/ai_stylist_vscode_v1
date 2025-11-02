"""Face encoding helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class FaceEmbedding:
    """Wrapper for face embeddings."""

    vector: list[float]
    model: str


class FaceEncoder:
    """Interface for the face recognition backend."""

    def encode(self, image_bytes: bytes) -> FaceEmbedding:
        """Return the embedding representing the person's face."""

        raise NotImplementedError("Face encoder integration pending.")
