"""
Main Entrypoint for CAGED FastAPI Backend Application.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.health import router as health_router
from app.config import settings
from app.core.exceptions import CAGEDException, caged_exception_handler
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """App startup and shutdown lifespan context manager."""
    setup_logging(log_level="DEBUG" if settings.DEBUG else "INFO")
    logger.info("Initializing CAGED Backend Framework v%s", settings.VERSION)
    yield
    logger.info("Shutting down CAGED Backend Framework")


def create_app() -> FastAPI:
    """Factory function to build and configure the FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Causal Analysis for Guaranteed Engagement Degradation",
        lifespan=lifespan,
    )

    # Configure CORS for Frontend Development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Exception Handlers
    app.add_exception_handler(CAGEDException, caged_exception_handler)

    # Include API Routers
    app.include_router(health_router)
    app.include_router(dashboard_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
