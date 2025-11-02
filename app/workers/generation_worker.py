"""Celery worker responsible for image generation tasks."""

from __future__ import annotations

from celery import Celery

from app.config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "generation_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)


@celery_app.task
def generate_outfit_task(scene_payload: dict) -> dict:
    """Entry point that will trigger the image generation pipeline."""

    _ = scene_payload
    # Full implementation will orchestrate prompt building and generator client.
    return {"status": "scheduled"}
