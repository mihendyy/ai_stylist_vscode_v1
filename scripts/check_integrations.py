"""Run connectivity checks against external AI providers."""

from __future__ import annotations

import asyncio
from typing import Iterable

from app.integrations import IntegrationCheckResult, run_all_checks


def _format_result(result: IntegrationCheckResult) -> str:
    status = "✅" if result.success else "❌"
    return f"{status} {result.name}: {result.message}"


def print_results(results: Iterable[IntegrationCheckResult]) -> None:
    for result in results:
        print(_format_result(result))


def main() -> None:
    results = asyncio.run(run_all_checks())
    print_results(results)


if __name__ == "__main__":
    main()
