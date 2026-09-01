"""
Pydantic Schemas for Health Check Endpoint.
"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response schema for GET /health."""

    status: str = Field(default="ok", description="Service operational status")
    service: str = Field(default="caged", description="Service name identifier")
