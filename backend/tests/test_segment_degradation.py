"""
Unit Tests for Segment-Level Degradation Detection and Localization.
"""

from datetime import datetime, timezone
import pytest

from app.baselines.base import BaselinePrediction
from app.detection.segment_metric import SegmentDegradationDetector
from app.ingestion.models import MetricType


def test_localized_degradation_in_one_segment():
    """
    Tests localized degradation targeting heavy segment while casual segment remains unaffected.
    """
    detector = SegmentDegradationDetector(default_segment_threshold=4.0)

    # Base predictions for all segments
    base_pred = BaselinePrediction(expected_value=100.0, variance=1.0, std_dev=1.0, ci_lower=98.0, ci_upper=102.0)

    overall_obs = {MetricType.LIKE: 85.0}  # Drop of 15 across platform
    overall_pred = {MetricType.LIKE: base_pred}

    segment_obs = {
        "casual": {MetricType.LIKE: 100.0},     # 0 drop -> Z = 0.0 -> S = 0.0
        "regular": {MetricType.LIKE: 98.0},    # Slight drop Z = 2.0 -> S = 4.0
        "heavy": {MetricType.LIKE: 60.0},      # Massive drop Z = 40.0 -> S = 1600.0
    }

    segment_pred = {
        "casual": {MetricType.LIKE: base_pred},
        "regular": {MetricType.LIKE: base_pred},
        "heavy": {MetricType.LIKE: base_pred},
    }

    report = detector.evaluate_all_segments(
        overall_observed=overall_obs,
        overall_predictions=overall_pred,
        segment_observed=segment_obs,
        segment_predictions=segment_pred,
        policy_id="P003",
    )

    assert report.most_degraded_segment == "heavy"
    assert report.least_degraded_segment == "casual"
    assert report.is_localized is True

    # Check ranked order: heavy, regular, casual
    ranked_ids = [seg_id for seg_id, _ in report.ranked_segments]
    assert ranked_ids == ["heavy", "regular", "casual"]

    # Casual segment remains unaffected
    assert report.segment_results["casual"].composite_score == 0.0
    assert report.segment_results["casual"].is_degraded is False

    # Heavy segment is severely degraded
    assert report.segment_results["heavy"].is_degraded is True
    assert report.segment_results["heavy"].top_degraded_metric == MetricType.LIKE


def test_uniform_degradation_across_all_segments():
    """Tests uniform engagement drops across all segments."""
    detector = SegmentDegradationDetector(default_segment_threshold=4.0)

    base_pred = BaselinePrediction(expected_value=100.0, std_dev=1.0, ci_lower=98.0, ci_upper=102.0)

    overall_obs = {MetricType.COMMENT: 97.0}
    overall_pred = {MetricType.COMMENT: base_pred}

    segment_obs = {
        "casual": {MetricType.COMMENT: 97.0},
        "regular": {MetricType.COMMENT: 97.0},
        "heavy": {MetricType.COMMENT: 97.0},
    }

    segment_pred = {
        "casual": {MetricType.COMMENT: base_pred},
        "regular": {MetricType.COMMENT: base_pred},
        "heavy": {MetricType.COMMENT: base_pred},
    }

    report = detector.evaluate_all_segments(
        overall_observed=overall_obs,
        overall_predictions=overall_pred,
        segment_observed=segment_obs,
        segment_predictions=segment_pred,
    )

    # All segments have identical composite score S = 3.0^2 = 9.0
    for seg_id, res in report.segment_results.items():
        assert abs(res.composite_score - 9.0) <= 0.01

    # Uniform drop means is_localized should be False
    assert report.is_localized is False
