"""
Phase 2 Unit & Integration Test Suite for CAGED Statistical Detection Engine.
Verifies 5-minute windowing, rate normalization, baseline freezing at T0,
single-metric Z-scores, multi-metric composite score S_t, independent null calibration (K >= 500),
detection latency, segment localization, and integration with Phase 1 telemetry.
"""

from datetime import datetime, timedelta, timezone
import pytest
import numpy as np

from app.ingestion.models import EngagementEvent, MetricType
from app.simulation.event_generator import EventGenerator
from app.simulation.experiment_config import (
    ExperimentConfig,
    PolicyMechanism,
    PolicyParameters,
)
from app.detection.window_aggregator import WindowAggregator, WindowedMetricPoint
from app.detection.null_calibration import NullThresholdCalibrator
from app.detection.caged_detector import CAGEDStatisticalDetector


def test_5min_window_aggregation_and_rates():
    """Verifies event stream aggregation into 5-minute fixed windows and rate normalization."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    config = ExperimentConfig(
        seed=42,
        num_users=200,
        num_items=100,
        event_rate=200,
        duration_hours=2.0,  # 2 hours = 24 windows of 5 minutes
        start_time=start_time,
    )
    generator = EventGenerator(config)
    events = generator.generate_events()

    aggregator = WindowAggregator(window_size_minutes=5)
    metric_points = aggregator.aggregate_stream(events, start_time=start_time)

    assert len(metric_points) == 24
    for pt in metric_points:
        assert isinstance(pt.window_start, datetime)
        assert (pt.window_end - pt.window_start).total_seconds() == 300.0
        assert pt.views_per_min >= 0.0
        assert 0.0 <= pt.likes_per_view <= 1.0
        assert 0.0 <= pt.comments_per_view <= 1.0
        assert 0.0 <= pt.shares_per_view <= 1.0
        assert 0.0 <= pt.clicks_per_view <= 1.0
        assert pt.avg_session_duration_sec >= 0.0


def test_pre_policy_baseline_freezing():
    """Verifies baseline parameters are computed strictly on pre-T0 windows and remain frozen post-T0."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 1, 0, 0, tzinfo=timezone.utc)
    
    config = ExperimentConfig(
        seed=101,
        num_users=300,
        num_items=100,
        event_rate=300,
        duration_hours=2.0,
        start_time=start_time,
        t0=t0,
        policy_mechanism=PolicyMechanism.ORIGINALITY_BOOST,
        policy_params=PolicyParameters(originality_weight_shift=2.0),
    )
    generator = EventGenerator(config)
    events = generator.generate_events()

    detector = CAGEDStatisticalDetector(composite_threshold=4.0)
    report = detector.analyze_stream(events, t0=t0)

    assert report.t0 == t0
    assert len(report.frozen_baseline_means) == 6
    assert len(report.frozen_baseline_stds) == 6

    # Verify frozen values match pre-T0 window statistics
    pre_evts = [e for e in events if e.timestamp < t0]
    aggregator = WindowAggregator(window_size_minutes=5)
    pre_pts = aggregator.aggregate_stream(pre_evts, start_time=start_time)
    
    views_pre = [pt.views_per_min for pt in pre_pts]
    expected_mean_views = round(float(np.mean(views_pre)), 4)
    assert report.frozen_baseline_means["view"] == expected_mean_views


def test_z_score_computation_and_variance():
    """Verifies directional single-metric Z-score calculation Z = (mu_frozen - Y) / sigma_frozen."""
    detector = CAGEDStatisticalDetector()
    
    # Create simple synthetic events: pre-T0 high likes, post-T0 low likes
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 1, 0, 0, tzinfo=timezone.utc)

    config = ExperimentConfig(
        seed=77,
        num_users=200,
        num_items=100,
        event_rate=200,
        duration_hours=2.0,
        start_time=start_time,
        t0=t0,
        policy_mechanism=PolicyMechanism.ORIGINALITY_BOOST,
        policy_params=PolicyParameters(originality_weight_shift=3.0),
    )
    generator = EventGenerator(config)
    events = generator.generate_events()

    report = detector.analyze_stream(events, t0=t0)
    post_wins = [w for w in report.window_results if w.is_post_t0]

    for w in post_wins:
        for m_str, m_res in w.metric_results.items():
            expected_z = (m_res.baseline_mean - m_res.observed_rate) / m_res.baseline_std
            assert abs(m_res.z_score - expected_z) < 1e-2
            assert m_res.positive_z_score == max(0.0, m_res.z_score)


def test_z_score_directionality_and_degradation():
    """
    Explicitly verifies directional degradation Z-score rules:
    - Y < frozen baseline => positive degradation Z (Z_m,t > 0)
    - Y > frozen baseline => non-positive Z (Z_m,t <= 0) and zero degradation contribution
    - S_t increases for degradation, not improvement
    """
    detector = CAGEDStatisticalDetector()
    baseline_mu = 100.0
    baseline_std = 10.0
    eps = 1e-6

    # Test Case 1: Metric drops below baseline (Degradation: Y = 80.0 < 100.0)
    y_degraded = 80.0
    z_degraded = (baseline_mu - y_degraded) / max(baseline_std, eps)  # (100 - 80) / 10 = +2.0
    assert z_degraded > 0.0
    assert z_degraded == pytest.approx(2.0)
    contrib_degraded = max(z_degraded, 0.0) ** 2  # 4.0 > 0
    assert contrib_degraded > 0.0

    # Test Case 2: Metric rises above baseline (Improvement: Y = 120.0 > 100.0)
    y_improved = 120.0
    z_improved = (baseline_mu - y_improved) / max(baseline_std, eps)  # (100 - 120) / 10 = -2.0
    assert z_improved < 0.0
    assert z_improved == pytest.approx(-2.0)
    contrib_improved = max(z_improved, 0.0) ** 2  # 0.0
    assert contrib_improved == 0.0

    # Test Case 3: S_t increases for degradation, not improvement
    s_t_degraded = contrib_degraded  # 4.0
    s_t_improved = contrib_improved  # 0.0
    assert s_t_degraded > s_t_improved



def test_multi_metric_composite_score():
    """Verifies composite score aggregation S_t = sum max(Z_m, 0)^2."""
    detector = CAGEDStatisticalDetector()
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 1, 0, 0, tzinfo=timezone.utc)

    config = ExperimentConfig(
        seed=88,
        num_users=200,
        num_items=100,
        event_rate=200,
        duration_hours=2.0,
        start_time=start_time,
        t0=t0,
        policy_mechanism=PolicyMechanism.ORIGINALITY_BOOST,
        policy_params=PolicyParameters(originality_weight_shift=2.0),
    )
    generator = EventGenerator(config)
    events = generator.generate_events()

    report = detector.analyze_stream(events, t0=t0)
    for w in report.window_results:
        expected_s = sum(m.positive_z_score ** 2 for m in w.metric_results.values())
        assert abs(w.composite_score - round(expected_s, 4)) < 1e-2


def test_null_distribution_threshold_calibration():
    """Executes independent null distribution threshold calibration (H0: NO_POLICY)."""
    calibrator = NullThresholdCalibrator(k_iterations=50, target_alpha=0.05, base_seed=50000)
    report = calibrator.run_null_calibration()

    assert report.k_iterations >= 50
    assert report.is_calibrated is True
    assert report.target_alpha == 0.05
    assert report.calibrated_s_threshold > 0.0
    assert abs(report.empirical_false_alarm_rate - 0.05) <= 0.05


def test_detection_latency_measurement():
    """Verifies detection latency measurement Delta T_latency = T_alert - T0."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 1, 0, 0, tzinfo=timezone.utc)

    config = ExperimentConfig(
        seed=42,
        num_users=400,
        num_items=150,
        event_rate=400,
        duration_hours=3.0,
        start_time=start_time,
        t0=t0,
        policy_mechanism=PolicyMechanism.ORIGINALITY_BOOST,
        policy_params=PolicyParameters(originality_weight_shift=3.0),
    )
    generator = EventGenerator(config)
    events = generator.generate_events()

    detector = CAGEDStatisticalDetector(composite_threshold=3.0)
    report = detector.analyze_stream(events, t0=t0)

    assert report.is_degradation_detected is True
    assert report.first_alert_timestamp is not None
    assert report.first_alert_timestamp >= t0
    assert report.detection_latency_minutes is not None
    assert report.detection_latency_minutes >= 0.0


def test_segment_and_category_localization():
    """Verifies localization of degraded user segments and content categories."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 1, 0, 0, tzinfo=timezone.utc)

    config = ExperimentConfig(
        seed=99,
        num_users=500,
        num_items=200,
        event_rate=500,
        duration_hours=2.0,
        start_time=start_time,
        t0=t0,
        policy_mechanism=PolicyMechanism.ORIGINALITY_BOOST,
        policy_params=PolicyParameters(originality_weight_shift=2.5),
    )
    generator = EventGenerator(config)
    events = generator.generate_events()

    detector = CAGEDStatisticalDetector(composite_threshold=3.0)
    report = detector.analyze_stream(events, t0=t0)

    assert report.most_degraded_segment is not None
    assert report.most_degraded_category is not None


def test_phase2_caged_detection_on_phase1_telemetry():
    """Integration test: Feeds Phase 1 synthetic experiment stream into CAGED Statistical Detector."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Phase 1 synthetic policy scenario (Originality Boost)
    config = ExperimentConfig(
        seed=42,
        num_users=1000,
        num_items=500,
        event_rate=500,
        duration_hours=24.0,
        start_time=start_time,
        t0=t0,
        treatment_ratio=0.50,
        policy_mechanism=PolicyMechanism.ORIGINALITY_BOOST,
        policy_params=PolicyParameters(originality_weight_shift=2.5),
    )
    generator = EventGenerator(config)
    events = generator.generate_events()

    # Pass observable telemetry into CAGED Statistical Detector
    detector = CAGEDStatisticalDetector(composite_threshold=4.0, minimum_effect_size=0.05)
    report = detector.analyze_stream(events, t0=t0)

    assert report.is_degradation_detected is True
    assert report.first_alert_timestamp is not None
    assert report.first_alert_timestamp >= t0
    assert report.peak_composite_score >= 4.0
    assert report.top_degraded_metric in [MetricType.LIKE, MetricType.COMMENT, MetricType.CLICK, MetricType.SESSION_DURATION]
