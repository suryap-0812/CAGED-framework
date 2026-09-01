"""
Unit Tests for CAGED Health Check Endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(async_client: AsyncClient) -> None:
    """Tests that GET /health returns status 200 and expected JSON structure."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "caged"


@pytest.mark.asyncio
async def test_health_endpoint_json_keys(async_client: AsyncClient) -> None:
    """Verifies that GET /health payload exactly matches specified requirements."""
    response = await async_client.get("/health")
    data = response.json()
    
    assert "status" in data
    assert "service" in data
    assert len(data) == 2
