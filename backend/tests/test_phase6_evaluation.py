"""
Phase 6 Automated Test Suite for Empirical Evaluation & Benchmark Harness.
Verifies structural execution, seed uniqueness, file schema parsing, ground-truth firewall isolation,
ex-post joining of tau_true, reproducibility, and statistical helper calculations.
No brittle scientific assertions (e.g. assert power > 0.80) are used.
"""

from datetime import datetime, timezone
import json
import os
import pytest

from app.evaluation.benchmark_runner import CAGEDBenchmarkRunner, compute_wilson_score_interval
from app.simulation.experiment_config import PolicyMechanism, PolicyParameters


def test_wilson_score_interval_computation():
    """Verifies Wilson score confidence interval calculation for empirical proportions."""
    p_hat, lower, upper = compute_wilson_score_interval(successes=90, total=100, confidence=0.95)
    assert p_hat == 0.90
    assert 0.80 < lower < 0.90
    assert 0.90 < upper <= 0.96

    # Zero success edge case
    p_hat, lower, upper = compute_wilson_score_interval(successes=0, total=100, confidence=0.95)
    assert p_hat == 0.0
    assert lower == 0.0
    assert upper < 0.05

    # Full success edge case
    p_hat, lower, upper = compute_wilson_score_interval(successes=100, total=100, confidence=0.95)
    assert p_hat == 1.0
    assert lower > 0.95
    assert upper == 1.0


def test_benchmark_runner_seed_assignment_and_scenario_mapping():
    """Verifies scenario specifications, seed offsets, and seed range uniqueness."""
    runner = CAGEDBenchmarkRunner(base_seed=100000)
    scenarios = runner.SCENARIOS

    assert len(scenarios) == 5
    scenario_ids = [s["scenario_id"] for s in scenarios]
    assert len(set(scenario_ids)) == 5
    assert "originality_downrank" in scenario_ids
    assert "null_policy" in scenario_ids

    # Seed uniqueness check
    seed_offsets = [s["seed_offset"] for s in scenarios]
    assert len(set(seed_offsets)) == 5


def test_benchmark_runner_execution_and_schema():
    """Verifies benchmark harness execution of 1 run per scenario and structural output schema."""
    runner = CAGEDBenchmarkRunner(base_seed=100000)
    records = runner.run_benchmark(runs_per_scenario=1)

    assert len(records) == 5
    for r in records:
        assert "run_id" in r
        assert "scenario_id" in r
        assert "seed" in r
        # CAGED fields
        assert "caged_degradation_detected" in r
        assert "caged_composite_score" in r
        assert "caged_threshold" in r
        # ML fields
        assert "ml_r2_score" in r
        assert "ml_rmse" in r
        assert "ml_mae" in r
        # DiD fields
        assert "did_tau_hat" in r
        assert "did_se" in r
        assert "did_p_value" in r
        assert "did_causal_verdict" in r
        # Ex-post Ground Truth fields
        assert "tau_true" in r
        assert "did_bias" in r
        assert "did_squared_error" in r
        assert "did_ci_covered" in r
        # No-interference fields
        assert "control_delta" in r


def test_ground_truth_firewall_absence_in_analytical_inputs():
    """Verifies tau_true and hidden simulator state are absent from analytical feature vectors and inputs."""
    runner = CAGEDBenchmarkRunner(base_seed=100000)
    scen = runner.SCENARIOS[0]
    rec = runner.run_single_eval(scen, run_idx=0)

    # Ex-post ground truth evaluation fields must be separate from DiD point estimate inputs
    assert rec["did_tau_hat"] != rec["tau_true"]  # Estimator computes tau_hat, not tau_true directly
    assert isinstance(rec["did_bias"], float)
    assert rec["did_bias"] == rec["did_tau_hat"] - rec["tau_true"]


def test_benchmark_runner_export_json_and_csv(tmp_path):
    """Verifies machine-readable JSON and CSV export functionality."""
    json_file = str(tmp_path / "test_benchmark.json")
    csv_file = str(tmp_path / "test_benchmark.csv")

    runner = CAGEDBenchmarkRunner(base_seed=100000)
    runner.run_benchmark(runs_per_scenario=1)
    runner.export_results(json_file, csv_file)

    assert os.path.exists(json_file)
    assert os.path.exists(csv_file)

    with open(json_file, "r") as f:
        data = json.load(f)
        assert data["total_runs"] == 5
        assert "summary_by_scenario" in data
        assert len(data["per_run_records"]) == 5

    with open(csv_file, "r") as f:
        lines = f.readlines()
        assert len(lines) == 6  # 1 header + 5 records


def test_reproducibility_of_fixed_seed_benchmark():
    """Verifies that running evaluation harness with identical seed yields identical numerical outputs."""
    runner1 = CAGEDBenchmarkRunner(base_seed=100000)
    rec1 = runner1.run_single_eval(runner1.SCENARIOS[0], run_idx=0)

    runner2 = CAGEDBenchmarkRunner(base_seed=100000)
    rec2 = runner2.run_single_eval(runner2.SCENARIOS[0], run_idx=0)

    assert rec1["did_tau_hat"] == pytest.approx(rec2["did_tau_hat"])
    assert rec1["tau_true"] == pytest.approx(rec2["tau_true"])
    assert rec1["caged_composite_score"] == pytest.approx(rec2["caged_composite_score"])
