"""
Unit Tests for Phase 20 REST API Endpoints.
"""

from fastapi.testclient import TestClient
import pytest

from app.main import app

client = TestClient(app)


def test_metrics_api_endpoints():
    """Tests GET /api/v1/metrics and GET /api/v1/metrics/{metric}."""
    res = client.get("/api/v1/metrics")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] >= 3

    res_like = client.get("/api/v1/metrics/like")
    assert res_like.status_code == 200
    assert res_like.json()["metric_type"] == "like"


def test_policies_api_endpoints():
    """Tests GET /api/v1/policies, POST /api/v1/policies, and GET /api/v1/policies/{policy_id}."""
    res_list = client.get("/api/v1/policies")
    assert res_list.status_code == 200
    assert res_list.json()["count"] >= 1

    # Create new policy
    new_pol = {
        "policy_id": "P_TEST_API",
        "policy_name": "API Test Policy",
        "description": "Registered via REST API test",
        "impact_factor": 0.85,
    }
    res_create = client.post("/api/v1/policies", json=new_pol)
    assert res_create.status_code == 200
    assert res_create.json()["status"] == "success"

    # Get created policy
    res_get = client.get("/api/v1/policies/P_TEST_API")
    assert res_get.status_code == 200
    assert res_get.json()["policy_name"] == "API Test Policy"


def test_alerts_and_reports_api_endpoints():
    """Tests GET /api/v1/alerts, GET /api/v1/segments, and GET /api/v1/reports."""
    res_alerts = client.get("/api/v1/alerts")
    assert res_alerts.status_code == 200

    res_segments = client.get("/api/v1/segments")
    assert res_segments.status_code == 200
    assert "segment_results" in res_segments.json()

    res_reports = client.get("/api/v1/reports")
    assert res_reports.status_code == 200
    assert res_reports.json()["count"] >= 1


def test_simulation_and_experiment_endpoints():
    """Tests /simulation and /experiments control endpoints."""
    res_status = client.get("/api/v1/simulation/status")
    assert res_status.status_code == 200
    assert "is_running" in res_status.json()

    res_stop = client.post("/api/v1/simulation/stop")
    assert res_stop.status_code == 200
    assert res_stop.json()["simulation"]["is_running"] is False

    res_start = client.post("/api/v1/simulation/start")
    assert res_start.status_code == 200
    assert res_start.json()["simulation"]["is_running"] is True

    res_exp = client.post("/api/v1/experiments/run", json={"scenario_name": "API Exp", "impact_factor": 0.75})
    assert res_exp.status_code == 200
    assert "experiment_id" in res_exp.json()
