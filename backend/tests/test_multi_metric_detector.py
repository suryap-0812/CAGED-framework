"""
Unit Tests for Multi-Metric Composite Degradation Score Detector.
"""

from datetime import datetime, timezone
import pytest

from app.baselines.base import BaselinePrediction
from app.detection.multi_metric import MultiMetricDetector
from app.ingestion.models import MetricType


def test_master_prompt_example_multi_metric_score():
    """
    Tests exact example from Master Prompt:
    likes Z = 3.1, comments Z = 2.7, shares Z = 3.4
    
    Expected S = (3.1)^2 + (2.7)^2 + (3.4)^2 = 9.61 + 7.29 + 11.56 = 28.46
    Top contributor: SHARES (Z = 3.4, sq_z = 11.56)
    """
    detector = MultiMetricDetector(default_composite_threshold=4.0)

    # Construct baselines and observations yielding target Z-scores
    # Z = (E - O) / sigma => O = E - Z * sigma (with sigma = 1.0, E = 100.0)
    baseline_preds = {
        MetricType.LIKE: BaselinePrediction(expected_value=100.0, variance=1.0, std_dev=1.0, ci_lower=98.0, ci_upper=102.0),
        MetricType.COMMENT: BaselinePrediction(expected_value=100.0, variance=1.0, std_dev=1.0, ci_lower=98.0, ci_upper=102.0),
        MetricType.SHARE: BaselinePrediction(expected_value=100.0, variance=1.0, std_dev=1.0, ci_lower=98.0, ci_upper=102.0),
    }

    observed = {
        MetricType.LIKE: 100.0 - 3.1,     # Z = 3.1
        MetricType.COMMENT: 100.0 - 2.7,  # Z = 2.7
        MetricType.SHARE: 100.0 - 3.4,    # Z = 3.4
    }

    result = detector.evaluate(
        observed_metrics=observed,
        baseline_predictions=baseline_preds,
        policy_id="P001",
    )

    # Score calculation: 3.1^2 (9.61) + 2.7^2 (7.29) + 3.4^2 (11.56) = 28.46
    assert abs(result.composite_score - 28.46) <= 0.05
    assert result.is_degraded is True
    assert result.top_contributor == MetricType.SHARE

    # Verify ranked contributions order: SHARE (3.4), LIKE (3.1), COMMENT (2.7)
    rankings = [c.metric_type for c in result.contributing_metrics]
    assert rankings == [MetricType.SHARE, MetricType.LIKE, MetricType.COMMENT]
    
    # Check share contribution percentage: 11.56 / 28.46 = 40.62%
    share_contrib = result.contributing_metrics[0]
    assert abs(share_contrib.contribution_percentage - 40.62) <= 0.5


def test_zero_degradation_composite_score():
    """Verifies composite score S = 0.0 when all observed engagement metrics meet or exceed baseline."""
    detector = MultiMetricDetector(default_composite_threshold=4.0)

    baseline_preds = {
        MetricType.LIKE: BaselinePrediction(expected_value=100.0, std_dev=2.0, ci_lower=96.0, ci_upper=104.0),
        MetricType.COMMENT: BaselinePrediction(expected_value=50.0, std_dev=1.0, ci_lower=48.0, ci_upper=52.0),
    }

    observed = {
        MetricType.LIKE: 105.0,     # Exceeds baseline -> Z = -2.5 -> max(Z, 0) = 0.0
        MetricType.COMMENT: 50.0,    # Equals baseline -> Z = 0.0 -> max(Z, 0) = 0.0
    }

    result = detector.evaluate(observed_metrics=observed, baseline_predictions=baseline_preds)

    assert result.composite_score == 0.0
    assert result.is_degraded is False
    assert result.top_contributor is None


def test_composite_thresholding():
    """Tests custom composite thresholds S_thresh."""
    detector = MultiMetricDetector()

    baseline_preds = {
        MetricType.LIKE: BaselinePrediction(expected_value=100.0, std_dev=1.0, ci_lower=98.0, ci_upper=102.0),
    }

    # Observed drop Z = 1.5 -> S = 1.5^2 = 2.25
    observed = {MetricType.LIKE: 98.5}

    # Evaluate with composite_threshold = 4.0 -> S=2.25 < 4.0 -> STABLE
    res_stable = detector.evaluate(
        observed_metrics=observed,
        baseline_predictions=baseline_preds,
        composite_threshold=4.0,
    )
    assert res_stable.composite_score == 2.25
    assert res_stable.is_degraded is False

    # Evaluate with composite_threshold = 2.0 -> S=2.25 >= 2.0 -> DEGRADED
    res_degraded = detector.evaluate(
        observed_metrics=observed,
        baseline_predictions=baseline_preds,
        composite_threshold=2.0,
    )
    assert res_degraded.is_degraded is True
