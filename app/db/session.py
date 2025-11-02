"""Database engine and session management."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import get_settings

settings = get_settings()

database_url = settings.database_url
if database_url.startswith("sqlite"):
    database_path = Path(make_url(database_url).database or "")
    if database_path.parent:
        database_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(database_url, echo=False, future=True)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    """Yield a managed asynchronous SQLAlchemy session."""

    async with AsyncSessionFactory() as session:
        yield session


async def init_db() -> None:
    """Create database tables if they do not exist."""

    from app.db import models  # noqa: WPS433 — import inside function to avoid cycles

    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
