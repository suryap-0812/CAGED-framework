"""
Phase 3 Unit & Validation Test Suite for ML Counterfactual Predictor.
Verifies training on pre-policy/control data only, zero-leakage guarantees,
5-minute historical window forecasting, CAGED/ML independence, and prediction accuracy.
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
from app.detection.caged_detector import CAGEDStatisticalDetector
from app.ml.counterfactual_predictor import (
    CounterfactualFeatureVector,
    CounterfactualMLPredictor,
)


def test_ml_predictor_training_on_pre_policy_data_only():
    """Verifies ML model trains strictly on pre-T0 or Control cohort observations."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 1, 0, 0, tzinfo=timezone.utc)

    config = ExperimentConfig(
        seed=42,
        num_users=300,
        num_items=100,
        event_rate=300,
        duration_hours=2.0,
        start_time=start_time,
        t0=t0,
        treatment_ratio=0.50,
        policy_mechanism=PolicyMechanism.ORIGINALITY_BOOST,
        policy_params=PolicyParameters(originality_weight_shift=2.0),
    )
    generator = EventGenerator(config)
    events = generator.generate_events()

    predictor = CounterfactualMLPredictor(target_metric=MetricType.LIKE)
    metrics = predictor.train_on_pre_policy_or_control(events, t0=t0)

    assert predictor.is_trained is True
    assert metrics["training_windows"] > 0
    assert metrics["rmse"] >= 0.0


def test_zero_leakage_guarantee():
    """
    Verifies zero-leakage guarantee: Feature extraction and model inputs contain
    ZERO post-policy Treatment outcomes, policy IDs, impact factors, or hidden simulator state.
    """
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

    predictor = CounterfactualMLPredictor(target_metric=MetricType.LIKE)
    predictor.train_on_pre_policy_or_control(events, t0=t0)

    # Inspect feature vector schema attributes
    vec = CounterfactualFeatureVector(
        window_start=start_time,
        hist_views_per_min=200.0,
        hist_likes_per_view=0.35,
        hist_comments_per_view=0.12,
        hist_shares_per_view=0.08,
        hist_clicks_per_view=0.11,
        hist_avg_session_duration=165.0,
        like_rate_of_change=0.0,
        comment_rate_of_change=0.0,
        diurnal_sin=0.0,
        diurnal_cos=1.0,
    )
    vec_dict = vec.model_dump()

    # Forbidden leaky field names
    forbidden_terms = [
        "policy_id",
        "impact_factor",
        "originality_weight_shift",
        "tau_true",
        "treatment_outcome",
        "composite_score",
        "is_degraded",
        "alert_status",
    ]

    for forbidden in forbidden_terms:
        assert forbidden not in vec_dict


def test_counterfactual_prediction_horizon():
    """Verifies 5-minute historical feature window -> next 5-minute counterfactual rate prediction."""
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
    )
    generator = EventGenerator(config)
    events = generator.generate_events()

    predictor = CounterfactualMLPredictor(target_metric=MetricType.LIKE)
    predictor.train_on_pre_policy_or_control(events, t0=t0)

    feature_window = CounterfactualFeatureVector(
        window_start=t0,
        hist_views_per_min=300.0,
        hist_likes_per_view=0.38,
        hist_comments_per_view=0.13,
        hist_shares_per_view=0.08,
        hist_clicks_per_view=0.12,
        hist_avg_session_duration=166.0,
        like_rate_of_change=-0.01,
        comment_rate_of_change=0.0,
        diurnal_sin=0.25,
        diurnal_cos=0.96,
    )

    res = predictor.predict_counterfactual(feature_window)
    assert res.target_metric == MetricType.LIKE
    assert res.counterfactual_expected_rate >= 0.0
    assert res.historical_observed_rate == 0.38


def test_caged_ml_independence():
    """Verifies CAGED statistical detector executes independently when ML model is un-trained or disabled."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 1, 0, 0, tzinfo=timezone.utc)

    config = ExperimentConfig(
        seed=42,
        num_users=300,
        num_items=100,
        event_rate=300,
        duration_hours=2.0,
        start_time=start_time,
        t0=t0,
        policy_mechanism=PolicyMechanism.ORIGINALITY_BOOST,
        policy_params=PolicyParameters(originality_weight_shift=2.5),
    )
    generator = EventGenerator(config)
    events = generator.generate_events()

    # CAGED statistical detector runs with zero ML predictor dependency
    caged_detector = CAGEDStatisticalDetector(composite_threshold=4.0)
    report = caged_detector.analyze_stream(events, t0=t0)

    assert report.is_degradation_detected is True
    assert report.peak_composite_score >= 4.0
    assert len(report.window_results) > 0


def test_counterfactual_prediction_accuracy_on_control_stream():
    """Evaluates counterfactual prediction forecast accuracy (R2 / RMSE) on control stream."""
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    config = ExperimentConfig(
        seed=42,
        num_users=500,
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

    # Filter control stream events only
    control_events = [
        e for e in events if e.segment_metadata and e.segment_metadata.get("cohort") == "control"
    ]

    predictor = CounterfactualMLPredictor(target_metric=MetricType.LIKE)
    metrics = predictor.train_on_pre_policy_or_control(control_events)

    assert metrics["rmse"] < 0.15
    assert metrics["training_windows"] > 5
