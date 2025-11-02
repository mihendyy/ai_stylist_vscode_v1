"""Tests for external integration connectivity helpers."""

from __future__ import annotations

import pytest
import pytest_mock

from app.config.settings import get_settings
from app.integrations.checks import (
    check_aitunnel_chat,
    check_aitunnel_images,
)


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AITUNNEL_API_KEY", "test-aitunnel")
    monkeypatch.setenv("AITUNNEL_BASE_URL", "https://aitunnel.test")
    monkeypatch.setenv("AITUNNEL_HEALTH_PATH", "/status")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_check_aitunnel_chat_success(mocker: pytest_mock.MockerFixture) -> None:
    client_mock = mocker.patch("app.integrations.checks.ChatGPTClient", autospec=True)
    instance = client_mock.return_value
    instance.ping = mocker.AsyncMock(return_value=True)
    instance.close = mocker.AsyncMock(return_value=None)

    result = await check_aitunnel_chat()

    assert result.success
    instance.ping.assert_awaited_once()
    instance.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_aitunnel_images_failure(mocker: pytest_mock.MockerFixture) -> None:
    client_mock = mocker.patch("app.integrations.checks.ImageGeneratorClient", autospec=True)
    instance = client_mock.return_value
    instance.ping = mocker.AsyncMock(return_value=False)
    instance.close = mocker.AsyncMock(return_value=None)

    result = await check_aitunnel_images()

    assert not result.success
    assert "non-success" in result.message.lower()
