"""Tests for external integration connectivity helpers."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.config.settings import get_settings
from app.integrations.checks import check_aitunnel, check_kie


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AITUNNEL_API_KEY", "test-aitunnel")
    monkeypatch.setenv("KIE_AI_API_KEY", "test-kie")
    monkeypatch.setenv("AITUNNEL_BASE_URL", "https://aitunnel.test")
    monkeypatch.setenv("KIE_BASE_URL", "https://kie.test")
    monkeypatch.setenv("AITUNNEL_HEALTH_PATH", "/health")
    monkeypatch.setenv("KIE_HEALTH_PATH", "/healthz")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
@respx.mock
async def test_check_aitunnel_success() -> None:
    respx.get("https://aitunnel.test/health").mock(return_value=Response(200))

    result = await check_aitunnel()

    assert result.success
    assert result.name == "AITunnel"


@pytest.mark.asyncio
@respx.mock
async def test_check_kie_failure() -> None:
    respx.get("https://kie.test/healthz").mock(return_value=Response(503))

    result = await check_kie()

    assert not result.success
    assert "non-success" in result.message.lower()
