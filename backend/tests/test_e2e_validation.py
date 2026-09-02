"""
Unit Tests for End-to-End Experimental Validation Pipeline.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "experiments")))
from e2e_validation import run_e2e_scenario


def test_e2e_null_hypothesis_scenario():
    """Verifies that Scenario 1 (No Degradation) correctly yields STABLE status."""
    res = run_e2e_scenario(
        scenario_name="Null Hypothesis Test",
        true_degraded=False,
        impact_factor=1.00,
    )
    assert res["detected_status"] == "STABLE"
    assert res["composite_score"] < 4.0
    assert res["passed"] is True


def test_e2e_degraded_scenario():
    """Verifies that Scenario 3 (Strong Degradation) correctly yields DEGRADED status."""
    res = run_e2e_scenario(
        scenario_name="Strong Drop Test",
        true_degraded=True,
        impact_factor=0.70,
    )
    assert res["detected_status"] == "DEGRADED"
    assert res["composite_score"] > 4.0
    assert res["passed"] is True


def test_e2e_metric_specific_degradation():
    """Verifies that targeted comment drop correctly identifies COMMENT as top degraded metric."""
    res = run_e2e_scenario(
        scenario_name="Comment Drop Test",
        true_degraded=True,
        impact_factor=0.50,
        target_metric="comment",
    )
    assert res["detected_status"] == "DEGRADED"
    assert res["top_degraded_metric"] == "COMMENT"
    assert res["passed"] is True
