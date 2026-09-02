"""
Unit Tests for Single-Metric Statistical Degradation Detector.
"""

from datetime import datetime, timezone
import pytest

from app.baselines.base import BaselinePrediction
from app.detection.single_metric import StatisticalDegradationDetector
from app.ingestion.models import MetricType


def test_no_degradation_observed_higher_than_expected():
    """Verifies that when observed engagement exceeds expected baseline, Z_deg = 0 and is_degraded = False."""
    detector = StatisticalDegradationDetector(default_threshold=2.0)
    
    baseline_pred = BaselinePrediction(
        expected_value=100.0,
        variance=4.0,
        std_dev=2.0,
        ci_lower=96.08,
        ci_upper=103.92,
    )

    # Observed O_t = 105.0 (greater than expected 100.0)
    res = detector.evaluate(
        metric_type=MetricType.LIKE,
        observed_value=105.0,
        baseline_prediction=baseline_pred,
        policy_id="P001",
    )

    assert res.deviation == -5.0
    assert res.z_score == -2.5
    assert res.positive_z_score == 0.0
    assert res.is_degraded is False
    assert res.status == "stable"


def test_small_degradation_below_threshold():
    """Verifies that small drops below expected yield positive Z-score below threshold."""
    detector = StatisticalDegradationDetector(default_threshold=2.0)

    baseline_pred = BaselinePrediction(
        expected_value=100.0,
        variance=4.0,
        std_dev=2.0,
        ci_lower=96.08,
        ci_upper=103.92,
    )

    # Observed O_t = 98.0 (1 std_dev drop) -> Z = 1.0 < 2.0
    res = detector.evaluate(
        metric_type=MetricType.COMMENT,
        observed_value=98.0,
        baseline_prediction=baseline_pred,
    )

    assert res.deviation == 2.0
    assert res.z_score == 1.0
    assert res.positive_z_score == 1.0
    assert res.is_degraded is False
    assert res.status == "stable"


def test_large_degradation_exceeding_threshold():
    """Verifies large engagement drops produce positive Z-score >= threshold and trigger degradation."""
    detector = StatisticalDegradationDetector(default_threshold=2.0)

    baseline_pred = BaselinePrediction(
        expected_value=100.0,
        variance=4.0,
        std_dev=2.0,
        ci_lower=96.08,
        ci_upper=103.92,
    )

    # Observed O_t = 90.0 (5 std_dev drop) -> Z = 5.0 >= 2.0
    res = detector.evaluate(
        metric_type=MetricType.SHARE,
        observed_value=90.0,
        baseline_prediction=baseline_pred,
        policy_id="P001",
    )

    assert res.deviation == 10.0
    assert res.z_score == 5.0
    assert res.positive_z_score == 5.0
    assert res.is_degraded is True
    assert res.p_value < 0.001
    assert res.status == "degraded"


def test_variance_change_sensitivity():
    """Verifies that higher baseline variance requires larger deviation to trigger degradation."""
    detector = StatisticalDegradationDetector(default_threshold=2.0)

    # Low variance baseline (std_dev = 1.0)
    low_var_pred = BaselinePrediction(expected_value=100.0, variance=1.0, std_dev=1.0, ci_lower=98.0, ci_upper=102.0)
    # High variance baseline (std_dev = 5.0)
    high_var_pred = BaselinePrediction(expected_value=100.0, variance=25.0, std_dev=5.0, ci_lower=90.0, ci_upper=110.0)

    # Same drop of 3.0 units:
    # Low var: Z = 3.0 / 1.0 = 3.0 -> DEGRADED
    res_low = detector.evaluate(MetricType.CLICK, observed_value=97.0, baseline_prediction=low_var_pred)
    assert res_low.is_degraded is True

    # High var: Z = 3.0 / 5.0 = 0.6 -> STABLE
    res_high = detector.evaluate(MetricType.CLICK, observed_value=97.0, baseline_prediction=high_var_pred)
    assert res_high.is_degraded is False


def test_zero_variance_baseline_safeguard():
    """Verifies that zero-variance baseline is floored to prevent division by zero."""
    detector = StatisticalDegradationDetector(default_threshold=2.0, min_std_dev=1e-4)

    zero_var_pred = BaselinePrediction(
        expected_value=100.0,
        variance=0.0,
        std_dev=0.0,
        ci_lower=100.0,
        ci_upper=100.0,
    )

    # Slight drop with zero variance -> uses min_std_dev floor
    res = detector.evaluate(MetricType.VIEW, observed_value=95.0, baseline_prediction=zero_var_pred)
    assert res.z_score > 0.0
    assert res.is_degraded is True


def test_missing_observed_or_baseline():
    """Verifies handling of missing values or uninitialized baselines."""
    detector = StatisticalDegradationDetector()

    res = detector.evaluate(MetricType.LIKE, observed_value=None, baseline_prediction=None)
    assert res.status == "insufficient_data"
    assert res.is_degraded is False
    assert res.p_value == 1.0
