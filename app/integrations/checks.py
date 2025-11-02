"""Connectivity checks for external AI providers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable

from app.imggen.generator_client import ImageGeneratorClient
from app.nlp.chatgpt_client import ChatGPTClient


@dataclass(slots=True)
class IntegrationCheckResult:
    """Structured result describing the integration check outcome."""

    name: str
    success: bool
    message: str


async def _run_check(
    name: str,
    factory: Callable[[], Awaitable[bool]],
    success_message: str,
) -> IntegrationCheckResult:
    try:
        result = await factory()
    except Exception as exc:  # pragma: no cover - defensive branch
        return IntegrationCheckResult(name=name, success=False, message=str(exc))

    if result:
        return IntegrationCheckResult(name=name, success=True, message=success_message)
    return IntegrationCheckResult(
        name=name,
        success=False,
        message="Service responded with non-success status.",
    )


async def check_aitunnel() -> IntegrationCheckResult:
    """Ping the AITunnel API and return the result."""

    client = ChatGPTClient()

    async def _ping() -> bool:
        try:
            return await client.ping()
        finally:
            await client.close()

    return await _run_check(
        name="AITunnel",
        factory=_ping,
        success_message="AITunnel API is reachable.",
    )


async def check_kie() -> IntegrationCheckResult:
    """Ping the KIE AI API and return the result."""

    client = ImageGeneratorClient()

    async def _ping() -> bool:
        try:
            return await client.ping()
        finally:
            await client.close()

    return await _run_check(
        name="KIE AI",
        factory=_ping,
        success_message="KIE AI API is reachable.",
    )


async def run_all_checks() -> list[IntegrationCheckResult]:
    """Execute all integration checks concurrently."""

    return await asyncio.gather(check_aitunnel(), check_kie())
