"""Storage helpers for persisting user media."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class StorageBackend(Protocol):
    """Defines a minimal interface for object storage backends."""

    async def save(self, key: str, data: bytes) -> str:
        ...

    async def delete(self, key: str) -> None:
        ...


class LocalStorage(StorageBackend):
    """
    Simple filesystem-based storage used in development.

    This allows us to avoid coupling to S3 while the core logic is being validated.
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    async def save(self, key: str, data: bytes) -> str:
        path = self._root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    async def delete(self, key: str) -> None:
        path = self._root / key
        if path.exists():
            path.unlink()
