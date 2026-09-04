"""
Phase 4 Unit & Validation Test Suite for Difference-in-Differences (DiD) Causal Estimator.
Verifies DiD calculation, negative policy effect, zero/no-effect null case, common external shocks,
pre-trend diagnostics, confidence intervals, practical significance, ground-truth firewall,
and compatibility with Phase 1 telemetry and CAGED detector outputs.
"""

from datetime import datetime, timedelta, timezone
import pytest
import numpy as np

from app.ingestion.models import EngagementEvent, MetricType
from app.simulation.event_generator import EventGenerator
from app.simulation.experiment_config import (
    ExperimentConfig,
    ExternalDisturbance,
    ExternalDisturbanceType,
    PolicyMechanism,
    PolicyParameters,
)
from app.detection.caged_detector import CAGEDStatisticalDetector
from app.causal.did_estimator import DiDEstimator


def test_basic_did_calculation():
    """Verifies basic DiD point estimate, standard error, 95% CI, p-value, and pre/post means."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    config = ExperimentConfig(
        seed=42,
        num_users=600,
        num_items=200,
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

    estimator = DiDEstimator(window_size_minutes=5)
    res = estimator.estimate_policy_effect(events, t0=t0, metric_type=MetricType.LIKE, minimum_effect_size=0.05)

    assert res.metric_type == MetricType.LIKE
    assert res.std_error > 0.0
    assert res.ci_lower <= res.tau_did <= res.ci_upper
    assert 0.0 <= res.p_value <= 1.0
    assert res.treat_pre_mean > 0.0
    assert res.control_pre_mean > 0.0
    assert res.window_counts["n_treat_pre"] > 0
    assert res.window_counts["n_control_post"] > 0


def test_negative_policy_effect():
    """Verifies negative policy effect estimation on Phase 1 Originality Boost scenario."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    config = ExperimentConfig(
        seed=42,
        num_users=800,
        num_items=300,
        event_rate=500,
        duration_hours=24.0,
        start_time=start_time,
        t0=t0,
        treatment_ratio=0.50,
        policy_mechanism=PolicyMechanism.ORIGINALITY_BOOST,
        policy_params=PolicyParameters(originality_weight_shift=3.0),
    )
    generator = EventGenerator(config)
    events = generator.generate_events()

    estimator = DiDEstimator(window_size_minutes=5)
    res = estimator.estimate_policy_effect(events, t0=t0, metric_type=MetricType.LIKE)

    assert res.tau_did < 0.0  # Directional degradation effect
    assert res.is_statistically_significant is True
    assert res.is_practically_significant is True
    assert "CAUSAL DEGRADATION CONFIRMED" in res.causal_verdict


def test_zero_no_effect_case():
    """Verifies tau_DiD ~ 0.0 and p > 0.05 on NO_POLICY null experiment stream."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    config = ExperimentConfig(
        seed=101,
        num_users=400,
        num_items=150,
        event_rate=300,
        duration_hours=24.0,
        start_time=start_time,
        t0=t0,
        treatment_ratio=0.50,
        policy_mechanism=PolicyMechanism.NO_POLICY,
    )
    generator = EventGenerator(config)
    events = generator.generate_events()

    estimator = DiDEstimator(window_size_minutes=5)
    res = estimator.estimate_policy_effect(events, t0=t0, metric_type=MetricType.LIKE)

    assert abs(res.tau_did) < 0.03
    assert res.p_value > 0.05
    assert res.is_statistically_significant is False
    assert "NO STATISTICALLY SIGNIFICANT EFFECT" in res.causal_verdict


def test_common_external_shock():
    """Verifies DiD accounts for common time-varying shock affecting Treatment & Control comparably."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    dist_time = datetime(2026, 9, 1, 15, 0, 0, tzinfo=timezone.utc)

    # Policy intervention + external disturbance shock affecting both cohorts
    config = ExperimentConfig(
        seed=42,
        num_users=800,
        num_items=300,
        event_rate=500,
        duration_hours=24.0,
        start_time=start_time,
        t0=t0,
        treatment_ratio=0.50,
        policy_mechanism=PolicyMechanism.ORIGINALITY_BOOST,
        policy_params=PolicyParameters(originality_weight_shift=2.5),
        external_disturbance=ExternalDisturbance(
            disturbance_type=ExternalDisturbanceType.GLOBAL_OUTAGE,
            onset_time=dist_time,
            duration_minutes=120.0,
            magnitude=0.70,  # 30% external traffic drop
            affects_control=True,
        ),
    )
    generator = EventGenerator(config)
    events = generator.generate_events()

    estimator = DiDEstimator(window_size_minutes=5)
    res = estimator.estimate_policy_effect(events, t0=t0, metric_type=MetricType.LIKE)

    assert res.tau_did < 0.0
    assert res.is_statistically_significant is True
    # DiD controls for common time-varying shock
    assert "Common time-varying shock exposure" in "".join(res.identification_assumptions)


def test_pre_trend_diagnostic():
    """Verifies pre-trend diagnostic test over pre-T0 data and exact required diagnostic message."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    config = ExperimentConfig(
        seed=42,
        num_users=600,
        num_items=200,
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

    estimator = DiDEstimator(window_size_minutes=5)
    res = estimator.estimate_policy_effect(events, t0=t0, metric_type=MetricType.LIKE)
    diag = res.pre_trend_diagnostic

    assert diag.p_value >= 0.0
    assert diag.is_parallel_trends_supported is True
    assert "If the pre-trend interaction is statistically insignificant (p > 0.05), there is insufficient evidence of differential pre-trends." in diag.diagnostic_message


def test_confidence_interval_and_std_error():
    """Verifies 95% confidence interval upper and lower bounds around point estimate tau_DiD."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    config = ExperimentConfig(
        seed=55,
        num_users=400,
        num_items=150,
        event_rate=400,
        duration_hours=24.0,
        start_time=start_time,
        t0=t0,
    )
    generator = EventGenerator(config)
    events = generator.generate_events()

    estimator = DiDEstimator(window_size_minutes=5)
    res = estimator.estimate_policy_effect(events, t0=t0, metric_type=MetricType.LIKE)

    expected_margin = 1.96 * res.std_error
    assert abs(res.ci_lower - (res.tau_did - expected_margin)) < 1e-3
    assert abs(res.ci_upper - (res.tau_did + expected_margin)) < 1e-3


def test_practical_significance_distinction():
    """Verifies distinction between statistical significance (p < 0.05) and practical effect threshold Delta_min."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    config = ExperimentConfig(
        seed=42,
        num_users=600,
        num_items=200,
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

    estimator = DiDEstimator(window_size_minutes=5)
    
    # Test with very high minimum_effect_size threshold (e.g. 0.90 -> 90% drop)
    res_high = estimator.estimate_policy_effect(events, t0=t0, metric_type=MetricType.LIKE, minimum_effect_size=0.90)
    assert res_high.is_statistically_significant is True
    assert res_high.is_practically_significant is False
    assert "STATISTICALLY SIGNIFICANT BUT PRACTICALLY NEGLIGIBLE" in res_high.causal_verdict

    # Test with normal minimum_effect_size threshold (0.05 -> 5% drop)
    res_norm = estimator.estimate_policy_effect(events, t0=t0, metric_type=MetricType.LIKE, minimum_effect_size=0.05)
    assert res_norm.is_statistically_significant is True
    assert res_norm.is_practically_significant is True


def test_ground_truth_firewall_isolation():
    """Verifies DiD estimator operates on observable telemetry with zero hidden simulator state."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    config = ExperimentConfig(
        seed=42,
        num_users=300,
        num_items=100,
        event_rate=300,
        duration_hours=24.0,
        start_time=start_time,
        t0=t0,
    )
    generator = EventGenerator(config)
    events = generator.generate_events()

    for e in events:
        e_dict = e.model_dump()
        assert "tau_true" not in e_dict
        assert "impact_factor" not in e_dict
        assert "originality_weight_shift" not in e_dict

    estimator = DiDEstimator(window_size_minutes=5)
    res = estimator.estimate_policy_effect(events, t0=t0, metric_type=MetricType.LIKE)
    assert res.tau_did is not None


def test_treatment_control_isolation():
    """Verifies Treatment policy changes leave Control cohort pre/post rates invariant (SUTVA compliance)."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    config = ExperimentConfig(
        seed=42,
        num_users=600,
        num_items=200,
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

    estimator = DiDEstimator(window_size_minutes=5)
    res = estimator.estimate_policy_effect(events, t0=t0, metric_type=MetricType.LIKE)

    # Control cohort change delta_control should be near 0.0
    assert abs(res.control_change) < 0.02
    assert abs(res.control_post_mean - res.control_pre_mean) < 0.02


def test_compatibility_with_phase1_telemetry():
    """Verifies DiD estimator executes cleanly on Phase 1 synthetic experiment telemetry streams."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

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

    estimator = DiDEstimator(window_size_minutes=5)
    res = estimator.estimate_policy_effect(events, t0=t0, metric_type=MetricType.LIKE)

    assert res.treat_pre_mean > 0.0
    assert res.treat_post_mean < res.treat_pre_mean
    assert res.tau_did < 0.0


def test_compatibility_with_caged_outputs_without_coupling():
    """Verifies DiD estimator operates alongside CAGED Statistical Detector without tight internal class coupling."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    config = ExperimentConfig(
        seed=42,
        num_users=600,
        num_items=200,
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

    # 1. Run CAGED Statistical Detector independently
    caged_detector = CAGEDStatisticalDetector(composite_threshold=4.0)
    caged_report = caged_detector.analyze_stream(events, t0=t0)

    # 2. Run DiD Estimator independently
    did_estimator = DiDEstimator(window_size_minutes=5)
    did_report = did_estimator.estimate_policy_effect(events, t0=t0, metric_type=MetricType.LIKE)

    # Verify both produced valid, parallel analytical outputs
    assert caged_report.is_degradation_detected is True
    assert did_report.is_statistically_significant is True


def test_deterministic_known_answer_did():
    """Deterministic known-answer test with manually constructed telemetry where tau_DiD is known exactly."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 1, 0, 0, tzinfo=timezone.utc)  # T0 at 1h (12 windows pre, 12 windows post)
    
    events: List[EngagementEvent] = []
    
    # 24 windows of 5 minutes (12 pre, 12 post)
    # Treatment: Pre = 10 likes/window, Post = 7 likes/window -> Delta_tr = -3.0
    # Control: Pre = 10 likes/window, Post = 10 likes/window -> Delta_co = 0.0
    # Expected tau_DiD = -3.0 - 0.0 = -3.0
    
    for w in range(24):
        win_start = start_time + timedelta(minutes=5 * w)
        is_post = win_start >= t0
        
        # Treatment cohort events
        tr_count = 7 if is_post else 10
        for i in range(tr_count):
            events.append(
                EngagementEvent(
                    event_id=f"tr_{w}_{i}",
                    user_hash=f"tr_user_hash_{i:06d}",
                    item_id=f"item_{i}",
                    event_type="like",
                    metric_type=MetricType.LIKE,
                    timestamp=win_start + timedelta(seconds=i),
                    watch_duration_seconds=30.0,
                    completed=True,
                    segment_metadata={"cohort": "treatment"},
                )
            )
            
        # Control cohort events
        co_count = 10
        for i in range(co_count):
            events.append(
                EngagementEvent(
                    event_id=f"co_{w}_{i}",
                    user_hash=f"co_user_hash_{i:06d}",
                    item_id=f"item_{i}",
                    event_type="like",
                    metric_type=MetricType.LIKE,
                    timestamp=win_start + timedelta(seconds=i),
                    watch_duration_seconds=30.0,
                    completed=True,
                    segment_metadata={"cohort": "control"},
                )
            )

    estimator = DiDEstimator(window_size_minutes=5)
    res = estimator.estimate_policy_effect(events, t0=t0, metric_type=MetricType.LIKE)

    # Exact expected point estimate verification
    assert res.treat_pre_mean == 10.0
    assert res.treat_post_mean == 7.0
    assert res.control_pre_mean == 10.0
    assert res.control_post_mean == 10.0
    assert res.treat_change == -3.0
    assert res.control_change == 0.0
    assert res.tau_did == -3.0  # Exact deterministic known-answer tau_DiD
    assert res.is_statistically_significant is True
    assert res.is_practically_significant is True


def test_deterministic_differential_pre_trends_failure():
    """Deterministic pre-trend diagnostic test with deliberately different pre-trends ensuring violation detection."""
    from app.detection.window_aggregator import WindowedMetricPoint
    
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    # Construct 10 pre-policy windows with divergent slopes
    treat_pre: List[WindowedMetricPoint] = []
    ctrl_pre: List[WindowedMetricPoint] = []
    
    for w in range(10):
        w_time = start_time + timedelta(minutes=5 * w)
        # Treatment: steep linear increase y_tr = 0.10 + 0.05 * w
        # Control: flat line y_co = 0.10
        p_tr = WindowedMetricPoint(
            window_index=w,
            window_start=w_time,
            window_end=w_time + timedelta(minutes=5),
            likes_per_view=0.10 + 0.05 * float(w),
        )
        p_co = WindowedMetricPoint(
            window_index=w,
            window_start=w_time,
            window_end=w_time + timedelta(minutes=5),
            likes_per_view=0.10,
        )
        
        treat_pre.append(p_tr)
        ctrl_pre.append(p_co)

    estimator = DiDEstimator(window_size_minutes=5)
    diag = estimator._evaluate_pre_trends(treat_pre, ctrl_pre, MetricType.LIKE)

    assert diag.is_parallel_trends_supported is False
    assert diag.p_value <= 0.05
    assert "Statistically significant evidence of differential pre-trends detected" in diag.diagnostic_message
    assert diag.differential_trend_coef > 0.0




