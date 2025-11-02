"""FastAPI entrypoint and HTTP routes."""

from fastapi import FastAPI

from app.config.settings import get_settings


def create_app() -> FastAPI:
    """Initialise the FastAPI application."""

    settings = get_settings()
    app = FastAPI(
        title="AI Stylist API",
        version="0.1.0",
        docs_url="/docs" if settings.environment != "prod" else None,
        redoc_url="/redoc" if settings.environment != "prod" else None,
    )

    @app.get("/health", tags=["system"])
    async def health_check() -> dict[str, str]:
        """Simple health endpoint used for readiness probes."""

        return {"status": "ok"}

    return app


app = create_app()
