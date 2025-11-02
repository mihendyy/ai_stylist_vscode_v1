"""SQLAlchemy models describing the core domain tables."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.services.stages import OnboardingStage


class Base(DeclarativeBase):
    """Base class for ORM models."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class User(Base):
    """End user that interacts with the Telegram bot."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    language: Mapped[str | None] = mapped_column(String(10))
    city: Mapped[str | None] = mapped_column(String(64))
    preferences: Mapped[str | None] = mapped_column(Text)
    style_reference: Mapped[str | None] = mapped_column(Text)
    onboarding_stage: Mapped[str] = mapped_column(
        String(64),
        default=OnboardingStage.AWAITING_SELFIE.value,
    )
    pending_garment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    garments: Mapped[list["Garment"]] = relationship(back_populates="owner")
    feedback: Mapped[list["Feedback"]] = relationship(back_populates="user")


class Garment(Base):
    """Clothing item uploaded by the user."""

    __tablename__ = "garments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(256), nullable=False)
    item_type: Mapped[str] = mapped_column(String(32), default="garment", nullable=False)
    label: Mapped[str | None] = mapped_column(String(64))
    subclass: Mapped[str | None] = mapped_column(String(64))
    attributes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    owner: Mapped[User] = relationship(back_populates="garments")


class Feedback(Base):
    """User reaction to generated outfits."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    outfit_reference: Mapped[str] = mapped_column(String(128))
    is_positive: Mapped[bool] = mapped_column(Boolean, default=True)
    reason: Mapped[str | None] = mapped_column(String(128))

    user: Mapped[User] = relationship(back_populates="feedback")
