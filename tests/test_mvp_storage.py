"""Smoke tests for MVP storage helpers."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from mvp.storage import UserStorage


@pytest.mark.asyncio
async def test_load_creates_profile(tmp_path: Path) -> None:
    storage = UserStorage(tmp_path / "users", tmp_path / "generated")

    profile = await storage.load("test-user")

    assert profile.user_id == "test-user"
    assert profile.stage == "awaiting_selfie"
    assert (tmp_path / "users" / "test-user" / "profile.json").exists()


@pytest.mark.asyncio
async def test_add_garment_updates_profile(tmp_path: Path) -> None:
    storage = UserStorage(tmp_path / "users", tmp_path / "generated")
    profile = await storage.load("user-1")

    await storage.add_garment(profile, "top", "/tmp/file.jpg")
    reloaded = await storage.load("user-1")

    assert "/tmp/file.jpg" in reloaded.wardrobe["top"]


@pytest.mark.asyncio
async def test_reset_user_removes_profile(tmp_path: Path) -> None:
    storage = UserStorage(tmp_path / "users", tmp_path / "generated")
    profile = await storage.load("user-reset")
    await storage.add_garment(profile, "top", "/tmp/file.jpg")

    await storage.reset_user("user-reset")

    new_profile = await storage.load("user-reset")
    assert new_profile.wardrobe["top"] == []
    assert new_profile.selfie_path is None
