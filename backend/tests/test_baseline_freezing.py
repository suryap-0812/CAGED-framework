"""
Unit Tests for Pre-Policy Baseline Freezing & Counterfactual Isolation.
"""

from datetime import datetime, timezone
import numpy as np
import pytest

from app.baselines.exponential_smoothing import ExponentialSmoothingBaseline
from app.core.exceptions import ResourceNotFoundException
from app.ingestion.models import MetricType
from app.policy.freezer import BaselineSnapshotter


def test_baseline_learned_and_frozen_at_t0():
    """Verifies pre-policy baseline fitting and freezing at policy trigger time T0."""
    np_rng = np.random.default_rng(42)
    pre_policy_data = (100.0 + np_rng.normal(0, 1.0, size=50)).tolist()

    active_model = ExponentialSmoothingBaseline(alpha=0.3, beta=0.1)
    active_model.fit(pre_policy_data)

    snapshotter = BaselineSnapshotter()
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Freeze baseline at T0 for Policy P001 on LIKE metric
    snapshot = snapshotter.freeze_baseline(
        policy_id="P001",
        metric=MetricType.LIKE,
        baseline_model=active_model,
        frozen_at=t0,
    )

    assert snapshot.policy_id == "P001"
    assert snapshot.metric_type == MetricType.LIKE
    assert snapshot.frozen_at == t0

    # Retrieve frozen model
    frozen_model = snapshotter.get_frozen_model(policy_id="P001", metric=MetricType.LIKE)
    
    # Expected predictions from frozen model match active model at T0
    active_pred = active_model.predict()
    frozen_pred = frozen_model.predict()
    assert active_pred.expected_value == frozen_pred.expected_value


def test_post_policy_data_does_not_contaminate_frozen_baseline():
    """
    CRITICAL TEST: Ensures post-policy degradation data updates active model
    but strictly DOES NOT contaminate the frozen baseline.
    """
    np_rng = np.random.default_rng(42)
    pre_policy_data = (100.0 + np_rng.normal(0, 1.0, size=50)).tolist()

    active_model = ExponentialSmoothingBaseline(alpha=0.3, beta=0.1)
    active_model.fit(pre_policy_data)

    snapshotter = BaselineSnapshotter()
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Freeze baseline at T0
    snapshotter.freeze_baseline(policy_id="P001", metric=MetricType.LIKE, baseline_model=active_model, frozen_at=t0)
    
    frozen_pred_at_t0 = snapshotter.get_frozen_model("P001", MetricType.LIKE).predict().expected_value

    # Post-Policy period: Severe engagement drop (values drop from 100 to 50!)
    post_policy_degraded_data = (50.0 + np_rng.normal(0, 1.0, size=50)).tolist()

    for degraded_val in post_policy_degraded_data:
        active_model.update(degraded_val)

    # Active model has updated and dropped its level
    active_pred_post = active_model.predict().expected_value
    assert active_pred_post < 70.0  # Active model level dropped

    # Frozen baseline remains IMMUTABLE at pre-policy level (~100)
    frozen_model_after_post = snapshotter.get_frozen_model("P001", MetricType.LIKE)
    frozen_pred_post = frozen_model_after_post.predict().expected_value

    assert frozen_pred_post == frozen_pred_at_t0
    assert abs(frozen_pred_post - 100.0) <= 2.0  # Counterfactual reference preserved!


def test_multiple_policies_handled_safely():
    """Verifies distinct frozen baselines stored for multiple policy events (P001, P002)."""
    snapshotter = BaselineSnapshotter()

    # Pre-policy baseline for P001 (mean ~100)
    model1 = ExponentialSmoothingBaseline(alpha=0.2)
    model1.fit([100.0] * 20)
    snapshotter.freeze_baseline("P001", MetricType.COMMENT, model1, frozen_at=datetime(2026, 9, 1, 6, 0, tzinfo=timezone.utc))

    # Baseline before P002 (mean ~200)
    model2 = ExponentialSmoothingBaseline(alpha=0.2)
    model2.fit([200.0] * 20)
    snapshotter.freeze_baseline("P002", MetricType.COMMENT, model2, frozen_at=datetime(2026, 9, 1, 18, 0, tzinfo=timezone.utc))

    frozen_p1 = snapshotter.get_frozen_model("P001", MetricType.COMMENT)
    frozen_p2 = snapshotter.get_frozen_model("P002", MetricType.COMMENT)

    assert frozen_p1.predict().expected_value == 100.0
    assert frozen_p2.predict().expected_value == 200.0

    snapshots = snapshotter.list_snapshots()
    assert len(snapshots) == 2


def test_get_nonexistent_snapshot_raises_error():
    """Verifies that requesting a non-existent frozen baseline raises ResourceNotFoundException."""
    snapshotter = BaselineSnapshotter()
    with pytest.raises(ResourceNotFoundException):
        snapshotter.get_frozen_model("P_NONEXISTENT", MetricType.LIKE)
