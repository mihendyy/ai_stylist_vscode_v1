"""Business logic for managing user wardrobe."""

from __future__ import annotations

import uuid
from pathlib import Path
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.storage.backend import StorageBackend
from app.services.stages import OnboardingStage


class WardrobeService:
    """Facade over storage and database operations."""

    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage

    async def ensure_user(
        self,
        session: AsyncSession,
        *,
        telegram_id: str,
        language: str | None = None,
        city: str | None = None,
    ) -> models.User:
        """Return an existing user or create a new record."""

        stmt = select(models.User).where(models.User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            return user

        user = models.User(
            telegram_id=telegram_id,
            language=language,
            city=city,
            onboarding_stage=OnboardingStage.AWAITING_SELFIE.value,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    async def add_garment(
        self,
        session: AsyncSession,
        *,
        user: models.User,
        file_name: str,
        file_data: bytes,
        item_type: str = "garment",
        label: str | None = None,
    ) -> models.Garment:
        """Persist garment metadata and media."""

        extension = Path(file_name).suffix or ".jpg"
        key = f"{user.telegram_id}/{uuid.uuid4().hex}{extension}"
        storage_path = await self._storage.save(key, file_data)

        garment = models.Garment(
            owner_id=user.id,
            storage_path=storage_path,
            item_type=item_type,
            label=label,
        )
        session.add(garment)
        await session.commit()
        await session.refresh(garment)
        return garment

    async def save_selfie(
        self,
        session: AsyncSession,
        *,
        user: models.User,
        file_name: str,
        file_data: bytes,
    ) -> models.Garment:
        """Persist or replace the user's profile photo."""

        await self.remove_existing_selfie(session, user=user)
        return await self.add_garment(
            session,
            user=user,
            file_name=file_name,
            file_data=file_data,
            item_type="selfie",
        )

    async def list_user_garments(
        self,
        session: AsyncSession,
        *,
        user: models.User,
        include_inactive: bool = False,
    ) -> list[models.Garment]:
        """Return garments uploaded by the given user."""

        stmt = select(models.Garment).where(
            models.Garment.owner_id == user.id,
            models.Garment.item_type == "garment",
        )
        if not include_inactive:
            stmt = stmt.where(models.Garment.is_active.is_(True))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_selfie(
        self,
        session: AsyncSession,
        *,
        user: models.User,
    ) -> models.Garment | None:
        """Return the stored selfie if present."""

        stmt = (
            select(models.Garment)
            .where(
                models.Garment.owner_id == user.id,
                models.Garment.item_type == "selfie",
            )
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def remove_existing_selfie(
        self,
        session: AsyncSession,
        *,
        user: models.User,
    ) -> None:
        """Remove existing selfie metadata if it exists."""

        selfie = await self.get_selfie(session, user=user)
        if not selfie:
            return
        await session.delete(selfie)
        await session.commit()

    async def update_stage(
        self,
        session: AsyncSession,
        *,
        user: models.User,
        stage: OnboardingStage,
    ) -> None:
        """Persist user onboarding stage."""

        user.onboarding_stage = stage.value
        session.add(user)
        await session.commit()

    async def update_style_reference(
        self,
        session: AsyncSession,
        *,
        user: models.User,
        style_reference: str,
    ) -> None:
        """Store the user's style inspirations/preferences."""

        user.style_reference = style_reference
        session.add(user)
        await session.commit()

    async def set_pending_garment(
        self,
        session: AsyncSession,
        *,
        user: models.User,
        garment: models.Garment | None,
    ) -> None:
        """Store or clear the garment awaiting category confirmation."""

        user.pending_garment_id = garment.id if garment else None
        session.add(user)
        await session.commit()

    async def assign_garment_label(
        self,
        session: AsyncSession,
        *,
        garment_id: int,
        label: str,
    ) -> None:
        """Update garment label."""

        stmt = (
            update(models.Garment)
            .where(models.Garment.id == garment_id)
            .values(label=label)
        )
        await session.execute(stmt)
        await session.commit()

    async def get_pending_garment(
        self,
        session: AsyncSession,
        *,
        user: models.User,
    ) -> models.Garment | None:
        """Return garment awaiting user classification."""

        if not user.pending_garment_id:
            return None
        stmt = select(models.Garment).where(models.Garment.id == user.pending_garment_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def summarise_garments(
        self,
        session: AsyncSession,
        *,
        user: models.User,
    ) -> list[dict[str, str | int]]:
        """Return a lightweight summary of the wardrobe."""

        garments = await self.list_user_garments(session, user=user)
        return [
            {
                "id": garment.id,
                "label": garment.label or "неизвестно",
                "path": garment.storage_path,
            }
            for garment in garments
        ]
