"""
API Integration Tests for Phase 5 Endpoints.

Verifies:
1. Complete 4-pillar response structure
2. Schema validation
3. Ground-truth firewall (no hidden state leakage in analytical sections)
4. Deterministic scenario execution
5. Standalone endpoint execution (DiD, ML, Scenarios)
6. Error handling for invalid configurations
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_scenarios_endpoint():
    """Verify GET /api/v1/phase5/scenarios returns predefined scenarios."""
    response = client.get("/api/v1/phase5/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert "scenarios" in data
    assert len(data["scenarios"]) >= 3
    scenario_ids = [s["scenario_id"] for s in data["scenarios"]]
    assert "originality_downrank" in scenario_ids
    assert "quality_filtering" in scenario_ids
    assert "null_policy" in scenario_ids


def test_run_experiment_4_pillar_response():
    """Verify POST /api/v1/phase5/run-experiment returns complete 4-pillar payload."""
    payload = {
        "scenario_id": "originality_downrank",
        "num_users": 60,
        "num_creators": 15,
        "num_items": 30,
        "pre_periods": 5,
        "post_periods": 5,
        "originality_weight_shift": -0.6,
        "random_seed": 42,
    }
    response = client.post("/api/v1/phase5/run-experiment", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Check 4 Pillars presence
    assert "pillar1_simulator" in data
    assert "pillar2_caged" in data
    assert "pillar3_ml" in data
    assert "pillar4_did" in data
    assert "summary" in data

    # Check Pillar 1 Simulator
    p1 = data["pillar1_simulator"]
    assert p1["scenario_id"] == "originality_downrank"
    assert p1["total_periods"] == 10
    assert "ground_truth_config" in p1
    assert "telemetry_records" in p1
    assert len(p1["telemetry_records"]) > 0

    # Check Pillar 2 CAGED Detection
    p2 = data["pillar2_caged"]
    assert "composite_statistic_St" in p2
    assert "calibrated_threshold" in p2
    assert "is_degradation_detected" in p2
    assert "pre_policy_baseline" in p2
    assert "metric_z_scores" in p2

    # Check Pillar 3 ML Predictor
    p3 = data["pillar3_ml"]
    assert p3["model_type"] in ["RidgeRegression_Lag1", "GradientBoosting_Lag1"]
    assert "r2_score_test_set" in p3
    assert "rmse_test_set" in p3
    assert "evaluation_data_split" in p3
    assert "predictions" in p3
    assert "Observed vs Counterfactual Prediction" in p3["evaluation_data_split"]

    # Check Pillar 4 DiD Causal Analysis
    p4 = data["pillar4_did"]
    assert "did_estimate_tau" in p4
    assert "standard_error_se" in p4
    assert "ci_95_lower" in p4
    assert "ci_95_upper" in p4
    assert "p_value" in p4
    assert "pre_trend_p_value" in p4
    assert "parallel_pre_trends_supported" in p4
    assert "relative_effect_size" in p4
    assert "causal_verdict" in p4


def test_ground_truth_firewall_leakage_prevention():
    """Verify ground truth state parameters are NOT leaked into analytical result blocks."""
    payload = {
        "scenario_id": "originality_downrank",
        "num_users": 60,
        "num_creators": 15,
        "num_items": 30,
        "pre_periods": 5,
        "post_periods": 5,
        "originality_weight_shift": -0.6,
        "random_seed": 42,
    }
    response = client.post("/api/v1/phase5/run-experiment", json=payload)
    assert response.status_code == 200
    data = response.json()

    hidden_keys = ["tau_true", "impact_factor", "originality_weight_shift", "hidden_ranking_params"]

    # Check Pillar 2 analytical output for hidden leaks
    for key in hidden_keys:
        assert key not in data["pillar2_caged"], f"Leakage detected: {key} in pillar2_caged"

    # Check Pillar 3 analytical output for hidden leaks
    for key in hidden_keys:
        assert key not in data["pillar3_ml"], f"Leakage detected: {key} in pillar3_ml"

    # Check Pillar 4 analytical output for hidden leaks
    for key in hidden_keys:
        assert key not in data["pillar4_did"], f"Leakage detected: {key} in pillar4_did"


def test_reproducible_experiment_execution():
    """Verify that using the same random seed yields identical telemetry and DiD estimates."""
    payload = {
        "scenario_id": "quality_filtering",
        "num_users": 50,
        "num_creators": 10,
        "num_items": 20,
        "pre_periods": 5,
        "post_periods": 5,
        "random_seed": 999,
    }
    res1 = client.post("/api/v1/phase5/run-experiment", json=payload).json()
    res2 = client.post("/api/v1/phase5/run-experiment", json=payload).json()

    # Telemetry should be identical
    t1 = res1["pillar1_simulator"]["telemetry_records"]
    t2 = res2["pillar1_simulator"]["telemetry_records"]
    assert len(t1) == len(t2)
    assert t1[0]["watch_completion_rate"] == t2[0]["watch_completion_rate"]

    # DiD estimate should be identical
    assert res1["pillar4_did"]["did_estimate_tau"] == res2["pillar4_did"]["did_estimate_tau"]


def test_standalone_did_estimate_endpoint():
    """Verify POST /api/v1/phase5/did-estimate endpoint works independently."""
    payload = {
        "metric_type": "watch_completion_rate",
        "pre_periods": 5,
        "post_periods": 5,
        "treatment_pre_values": [0.8, 0.81, 0.79, 0.82, 0.80],
        "treatment_post_values": [0.6, 0.59, 0.61, 0.58, 0.62],
        "control_pre_values": [0.8, 0.79, 0.81, 0.80, 0.80],
        "control_post_values": [0.81, 0.80, 0.79, 0.82, 0.80],
    }
    response = client.post("/api/v1/phase5/did-estimate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["metric_type"] == "watch_completion_rate"
    assert data["did_estimate_tau"] < -0.15
    assert data["standard_error_se"] > 0
    assert data["p_value"] <= 0.05
    assert data["relative_effect_size"] > 0.05
    assert data["causal_verdict"] == "CONFIRMED_DEGRADATION"


def test_standalone_ml_counterfactual_endpoint():
    """Verify POST /api/v1/phase5/ml-counterfactual endpoint works independently."""
    # Create simple telemetry
    telemetry = []
    for t in range(12):
        telemetry.append({
            "window_id": t,
            "period": t,
            "metric_name": "watch_completion_rate",
            "treatment_rate": 0.8 - (0.2 if t >= 6 else 0.0),
            "control_rate": 0.8,
        })

    payload = {
        "metric_type": "watch_completion_rate",
        "pre_periods": 6,
        "post_periods": 6,
        "telemetry_records": telemetry,
    }
    response = client.post("/api/v1/phase5/ml-counterfactual", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["model_type"] == "RidgeRegression_Lag1"
    assert "r2_score_test_set" in data
    assert "rmse_test_set" in data
    assert "evaluation_data_split" in data
    assert len(data["predictions"]) == 12


def test_invalid_experiment_configuration():
    """Verify validation handling for invalid inputs."""
    # Pre-periods < 3 should fail validation
    payload = {
        "scenario_id": "originality_downrank",
        "pre_periods": 1,
        "post_periods": 5,
    }
    response = client.post("/api/v1/phase5/run-experiment", json=payload)
    assert response.status_code == 422  # Unprocessable Entity (Pydantic validation error)
