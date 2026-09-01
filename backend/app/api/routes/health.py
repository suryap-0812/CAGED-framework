"""
Health Check API Route Definition.
"""

from fastapi import APIRouter
from app.api.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Returns the operational status of the CAGED service."""
    return HealthResponse(status="ok", service="caged")
