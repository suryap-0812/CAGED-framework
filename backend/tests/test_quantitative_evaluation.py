"""
Unit Tests for Phase 25 Quantitative Evaluation & Method Comparison Benchmark.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "experiments", "evaluation")))
from quantitative_benchmark import (
    evaluate_method_a_static_baseline,
    evaluate_method_b_caged_framework,
    evaluate_method_c_caged_plus_ml,
)
from app.experiments.scenarios import get_predefined_scenarios


def test_quantitative_method_comparison_metrics():
    """Verifies that quantitative evaluation metrics are calculated cleanly for Methods A, B, and C."""
    scenarios = get_predefined_scenarios()

    res_a = evaluate_method_a_static_baseline(scenarios)
    res_b = evaluate_method_b_caged_framework(scenarios)
    res_c = evaluate_method_c_caged_plus_ml(scenarios)

    # Method B (CAGED Framework) must outperform Method A (Static Baseline) on F1, Memory, and Throughput
    assert res_b["f1"] > res_a["f1"]
    assert res_b["precision"] == 1.0000
    assert res_b["recall"] == 1.0000
    assert res_b["fpr"] < res_a["fpr"]
    assert res_b["segment_accuracy"] == "100.0%"

    # Method C (CAGED + ML) must achieve early warning delay
    assert "Early Warning" in res_c["delay"]
