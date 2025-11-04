"""Simple JSON-backed storage for user profiles."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import shutil

DEFAULT_WARDROBE = {
    "top": [],
    "bottom": [],
    "shoes": [],
    "outerwear": [],
    "accessories": [],
}


@dataclass(slots=True)
class UserProfile:
    """Serializable representation of a Telegram user interacting with the bot."""

    user_id: str
    stage: str = "awaiting_selfie"
    selfie_path: Optional[str] = None
    preferences: Dict[str, Any] = field(
        default_factory=lambda: {
            "style_tags": [],
            "colors": [],
            "brand_refs": [],
            "notes": "",
        },
    )
    wardrobe: Dict[str, List[str]] = field(
        default_factory=lambda: {category: [] for category in DEFAULT_WARDROBE},
    )
    pending_item_path: Optional[str] = None
    daily_context: Dict[str, Any] = field(
        default_factory=lambda: {
            "occasion": "",
            "style_today": "",
            "weather": "",
            "notes": "",
        },
    )
    feedback_history: List[Dict[str, Any]] = field(default_factory=list)
    updated_at: Optional[str] = None

    def touch(self) -> None:
        """Update the modification timestamp."""

        self.updated_at = datetime.utcnow().isoformat()


class UserStorage:
    """Manages reading and writing user profiles as JSON files."""

    def __init__(self, root: Path, generated_root: Path) -> None:
        self._root = root
        self._generated_root = generated_root
        self._root.mkdir(parents=True, exist_ok=True)
        self._generated_root.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, asyncio.Lock] = {}

    def _profile_path(self, user_id: str) -> Path:
        return self._root / user_id / "profile.json"

    def ensure_user_dirs(self, user_id: str) -> tuple[Path, Path]:
        """Ensure directories exist and return (user_root, generated_root)."""

        user_dir = self._root / user_id
        generated_dir = self._generated_root / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        generated_dir.mkdir(parents=True, exist_ok=True)
        return user_dir, generated_dir

    def _lock_for(self, user_id: str) -> asyncio.Lock:
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]

    async def load(self, user_id: str) -> UserProfile:
        """Load an existing profile or create a new one."""

        async with self._lock_for(user_id):
            self.ensure_user_dirs(user_id)
            path = self._profile_path(user_id)
            if not path.exists():
                profile = UserProfile(user_id=user_id)
                profile.touch()
                await self._write_profile(path, profile)
                return profile
            data = await asyncio.to_thread(path.read_text, encoding="utf-8")
            payload = json.loads(data)
            profile = UserProfile(**payload)
            return profile

    async def save(self, profile: UserProfile) -> None:
        """Persist the profile to disk."""

        profile.touch()
        async with self._lock_for(profile.user_id):
            path = self._profile_path(profile.user_id)
            await self._write_profile(path, profile)

    async def _write_profile(self, path: Path, profile: UserProfile) -> None:
        body = json.dumps(asdict(profile), ensure_ascii=False, indent=2)
        await asyncio.to_thread(self._write_file, path, body)

    @staticmethod
    def _write_file(path: Path, body: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    async def add_garment(self, profile: UserProfile, category: str, file_path: str) -> None:
        """Append a garment path to the user's wardrobe."""

        category_key = category.lower()
        if category_key not in profile.wardrobe:
            profile.wardrobe[category_key] = []
        profile.wardrobe[category_key].append(file_path)
        await self.save(profile)

    async def set_selfie(self, profile: UserProfile, file_path: str) -> None:
        """Store selfie path and persist profile."""

        profile.selfie_path = file_path
        await self.save(profile)

    async def update_preferences(self, profile: UserProfile, preferences: Dict[str, Any]) -> None:
        """Replace stored preferences."""

        profile.preferences.update(preferences)
        await self.save(profile)

    async def update_daily_context(self, profile: UserProfile, context: Dict[str, Any]) -> None:
        """Merge daily outfit requirements."""

        profile.daily_context.update(context)
        await self.save(profile)

    async def add_feedback(self, profile: UserProfile, rating: str, note: str) -> None:
        """Persist user feedback."""

        profile.feedback_history.append(
            {
                "rating": rating,
                "note": note,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        await self.save(profile)

    async def set_stage(self, profile: UserProfile, stage: str) -> None:
        """Update the conversational stage."""

        profile.stage = stage
        await self.save(profile)

    async def set_pending_item(self, profile: UserProfile, file_path: Optional[str]) -> None:
        """Store path of the garment pending category selection."""

        profile.pending_item_path = file_path
        await self.save(profile)

    def get_generated_dir(self, user_id: str) -> Path:
        """Return (and create) directory for generated images."""

        _, generated = self.ensure_user_dirs(user_id)
        return generated

    async def reset_user(self, user_id: str) -> None:
        """Remove stored data for the given user."""

        async with self._lock_for(user_id):
            user_dir = self._root / user_id
            generated_dir = self._generated_root / user_id
            await asyncio.gather(
                asyncio.to_thread(self._delete_dir, user_dir),
                asyncio.to_thread(self._delete_dir, generated_dir),
            )

    @staticmethod
    def _delete_dir(path: Path) -> None:
        if path.exists():
            shutil.rmtree(path)
