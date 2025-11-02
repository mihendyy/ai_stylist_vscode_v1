"""Authentication helpers and route dependencies."""

from fastapi import Depends, Header, HTTPException, status

from app.config.settings import get_settings


def require_internal_token(
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
) -> None:
    """
    Ensure that administrative endpoints are protected by an internal token.

    For MVP this is a simple shared-secret validation. Later we can replace it with
    proper user management or OAuth integration.
    """

    settings = get_settings()
    expected_token = settings.aitunnel_api_key  # reuse until admin auth is defined
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin key is not configured.",
        )

    if x_internal_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative token.",
        )


InternalAuthDependency = Depends(require_internal_token)
