"""
Phase 1 Unit Tests for CAGED Simulation Engine.
Verifies ContentCatalog, RecommendationEngine, UserBehaviorModel, ExperimentConfig,
SUTVA no-interference, and Ground-Truth Firewall Isolation.
"""

from datetime import datetime, timedelta, timezone
import pytest

from app.ingestion.models import EngagementEvent, MetricType
from app.simulation.content_catalog import ContentCatalog
from app.simulation.experiment_config import (
    ExperimentConfig,
    ExternalDisturbance,
    ExternalDisturbanceType,
    PolicyMechanism,
    PolicyParameters,
)
from app.simulation.event_generator import EventGenerator
from app.simulation.recommender import RecommendationEngine
from app.simulation.user_behavior import UserBehaviorModel
from app.simulation.user_profile import UserProfile, UserSegment, create_synthetic_user_profile


def test_content_catalog_reproducibility():
    """Verifies content catalog generation and seed reproducibility."""
    cat1 = ContentCatalog(num_items=100, seed=42)
    cat2 = ContentCatalog(num_items=100, seed=42)
    cat3 = ContentCatalog(num_items=100, seed=99)

    assert len(cat1.items) == 100
    assert cat1.items[0].item_id == cat2.items[0].item_id
    assert cat1.items[0].quality_score == cat2.items[0].quality_score
    assert cat1.items[0].originality_score == cat2.items[0].originality_score

    # Different seed produces different catalog items
    assert cat1.items[0].quality_score != cat3.items[0].quality_score


def test_sutva_no_interference():
    """
    Verifies SUTVA no-interference assumption:
    Treatment-side policy changes post-T0 must NEVER modify control cohort ranking weights.
    """
    recommender = RecommendationEngine()
    params = PolicyParameters(originality_weight_shift=0.40)

    # Pre-T0 treatment vs control -> identical base weights
    w_treat_pre = recommender.get_cohort_ranking_weights(
        is_treatment=True, is_post_t0=False, mechanism=PolicyMechanism.ORIGINALITY_BOOST, params=params
    )
    w_control_pre = recommender.get_cohort_ranking_weights(
        is_treatment=False, is_post_t0=False, mechanism=PolicyMechanism.ORIGINALITY_BOOST, params=params
    )
    assert w_treat_pre == w_control_pre

    # Post-T0 treatment vs control -> Control MUST preserve base weights (SUTVA hold)
    w_treat_post = recommender.get_cohort_ranking_weights(
        is_treatment=True, is_post_t0=True, mechanism=PolicyMechanism.ORIGINALITY_BOOST, params=params
    )
    w_control_post = recommender.get_cohort_ranking_weights(
        is_treatment=False, is_post_t0=True, mechanism=PolicyMechanism.ORIGINALITY_BOOST, params=params
    )

    assert w_control_post == w_control_pre  # Control unchanged
    assert w_treat_post.originality_weight > w_control_post.originality_weight  # Treatment shifted


def test_emergent_user_behavior():
    """
    Verifies that engagement actions (likes, comments) emerge from watch completion
    driven by content quality and user preference.
    """
    user = create_synthetic_user_profile(
        user_index=1, segment=UserSegment.REGULAR, available_categories=["education", "gaming"]
    )
    catalog = ContentCatalog(num_items=10, seed=42)
    item_high_quality = catalog.items[0]
    item_high_quality.quality_score = 0.95
    item_high_quality.category = user.preferred_categories[0]

    behavior_model = UserBehaviorModel()
    outcomes = [
        behavior_model.process_impression(user, item_high_quality) for _ in range(50)
    ]

    avg_completion = sum(o.watch_completion_fraction for o in outcomes) / 50.0
    like_count = sum(1 for o in outcomes if o.liked)

    # High quality + preferred category yields higher watch completion and non-zero likes
    assert avg_completion > 0.50
    assert like_count > 0


def test_treatment_control_stream_generation():
    """
    Verifies parallel Treatment & Control stream event generation.
    """
    start = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    config = ExperimentConfig(
        seed=42,
        num_users=100,
        num_items=50,
        event_rate=20,
        treatment_ratio=0.50,
        start_time=start,
        t0=start + timedelta(hours=6),
        duration_hours=12.0,
        policy_mechanism=PolicyMechanism.ORIGINALITY_BOOST,
    )

    generator = EventGenerator(config=config)
    events = generator.generate_events()

    assert len(events) > 0
    cohorts = set(e.segment_metadata.get("cohort") for e in events if e.segment_metadata)
    assert "treatment" in cohorts
    assert "control" in cohorts


def test_ground_truth_firewall_isolation():
    """
    Verifies Strict Ground-Truth Firewall Isolation:
    Emitted EngagementEvent objects must contain ZERO hidden policy parameter state or effect sizes.
    """
    config = ExperimentConfig(
        seed=42,
        policy_mechanism=PolicyMechanism.ORIGINALITY_BOOST,
        policy_params=PolicyParameters(originality_weight_shift=0.50),
    )
    generator = EventGenerator(config=config)
    events = generator.generate_events()

    # Inspect event fields for leaks
    for e in events[:100]:
        event_dict = e.model_dump()
        assert "policy_params" not in event_dict
        assert "originality_weight_shift" not in event_dict
        assert "effect_magnitude" not in event_dict
        assert "tau_true" not in event_dict
