"""
Unit Tests for Optional Early-Warning ML Degradation Predictor.
"""

from datetime import datetime, timezone
import pytest

from app.ingestion.models import MetricType
from app.ml.dataset import MLFeatureDatasetBuilder, MLFeatureVector
from app.ml.predictor import XGBoostDegradationPredictor


def test_ml_feature_dataset_builder():
    """Tests synthetic dataset generation and feature vector creation."""
    X, y, vectors = MLFeatureDatasetBuilder.generate_synthetic_dataset(num_samples=100, seed=42)

    assert len(X) == 100
    assert len(y) == 100
    assert X.shape[1] == 13
    assert set(y).issubset({0, 1})

    vec = vectors[0]
    assert isinstance(vec, MLFeatureVector)
    assert len(vec.to_numpy()) == 13


def test_ml_predictor_training_and_probabilities():
    """Tests training ML model, probability outputs in [0, 1], and warning status levels."""
    X, y, vectors = MLFeatureDatasetBuilder.generate_synthetic_dataset(num_samples=200, seed=42)

    predictor = XGBoostDegradationPredictor(prediction_horizon_minutes=15, random_state=42)
    metrics = predictor.train(X, y)

    assert predictor.is_trained is True
    assert metrics["auc"] >= 0.80
    assert metrics["f1"] >= 0.70

    # Predict on non-degraded feature vector
    normal_vec = MLFeatureDatasetBuilder.build_feature_vector(
        timestamp=datetime.now(timezone.utc),
        metric_means={MetricType.LIKE: 100.0, MetricType.COMMENT: 50.0, MetricType.SHARE: 20.0},
        metric_z_scores={MetricType.LIKE: 0.0, MetricType.COMMENT: 0.0, MetricType.SHARE: 0.0},
        metric_rates_of_change={MetricType.LIKE: 0.0, MetricType.COMMENT: 0.0, MetricType.SHARE: 0.0},
        composite_s_score=0.0,
    )

    res_normal = predictor.predict_degradation_probability(normal_vec)
    assert 0.0 <= res_normal.degradation_probability <= 1.0
    assert res_normal.warning_status in ["NORMAL", "WATCH"]

    # Predict on highly degraded feature vector
    degraded_vec = MLFeatureDatasetBuilder.build_feature_vector(
        timestamp=datetime.now(timezone.utc),
        metric_means={MetricType.LIKE: 70.0, MetricType.COMMENT: 30.0, MetricType.SHARE: 10.0},
        metric_z_scores={MetricType.LIKE: 3.5, MetricType.COMMENT: 3.0, MetricType.SHARE: 3.2},
        metric_rates_of_change={MetricType.LIKE: -0.20, MetricType.COMMENT: -0.15, MetricType.SHARE: -0.18},
        composite_s_score=31.49,
    )

    res_degraded = predictor.predict_degradation_probability(degraded_vec)
    assert 0.0 <= res_degraded.degradation_probability <= 1.0
    assert res_degraded.degradation_probability >= 0.50
    assert res_degraded.warning_status in ["WARNING", "CRITICAL"]

    # Feature importances check
    importances = predictor.get_feature_importances()
    assert len(importances) == 13
    assert sum(importances.values()) > 0.0


def test_ml_predictor_safe_fallback_when_untrained_or_disabled():
    """
    CRITICAL TEST: Ensures framework works fine and returns safe fallback
    if ML predictor is un-trained, fails, or disabled.
    """
    predictor = XGBoostDegradationPredictor(prediction_horizon_minutes=15)
    assert predictor.is_trained is False

    test_vec = MLFeatureDatasetBuilder.build_feature_vector(
        timestamp=datetime.now(timezone.utc),
        metric_means={MetricType.LIKE: 100.0},
        metric_z_scores={MetricType.LIKE: 0.0},
        metric_rates_of_change={MetricType.LIKE: 0.0},
        composite_s_score=0.0,
    )

    res = predictor.predict_degradation_probability(test_vec)
    assert res.degradation_probability == 0.0
    assert res.warning_status == "NORMAL"
    assert res.feature_importances == {}
