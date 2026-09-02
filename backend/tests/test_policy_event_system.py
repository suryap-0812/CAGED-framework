"""
Unit Tests for Policy Event System & Policy Stream Injection.
"""

from datetime import datetime, timedelta, timezone
import pytest

from app.ingestion.models import MetricType
from app.policy.models import PolicyEvent, PolicyMetadata
from app.policy.registry import PolicyRegistry, PolicyTimeline
from app.policy.trigger import PolicyTrigger
from app.simulation.event_generator import EventGenerator, EventGeneratorConfig
from app.simulation.user_profile import UserSegment


def test_policy_event_creation_and_caged_metadata():
    """Verifies PolicyEvent creation and metadata extraction for CAGED."""
    p001 = PolicyEvent(
        policy_id="P001",
        policy_name="Global Engagement Reduction",
        timestamp=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        description="Global algorithm adjustment reducing recommendation distribution",
        impact_factor=0.80,
    )

    assert p001.policy_id == "P001"
    assert p001.timestamp.tzinfo == timezone.utc

    # Metadata extraction must NOT contain ground-truth target metrics or impact factors
    meta = p001.to_caged_metadata()
    assert isinstance(meta, PolicyMetadata)
    assert meta.policy_id == "P001"
    assert not hasattr(meta, "impact_factor")
    assert not hasattr(meta, "target_metric")


def test_policy_registry_and_timeline():
    """Tests PolicyRegistry and PolicyTimeline active policy checks at T0."""
    registry = PolicyRegistry()
    timeline = PolicyTimeline(registry)

    t0_p1 = datetime(2026, 9, 1, 6, 0, 0, tzinfo=timezone.utc)
    t0_p2 = datetime(2026, 9, 1, 18, 0, 0, tzinfo=timezone.utc)

    p1 = PolicyEvent(
        policy_id="P001",
        policy_name="Early Policy",
        timestamp=t0_p1,
        description="First policy adjustment",
    )
    p2 = PolicyEvent(
        policy_id="P002",
        policy_name="Late Policy",
        timestamp=t0_p2,
        description="Second policy adjustment",
    )

    timeline.add_policy_event(p1)
    timeline.add_policy_event(p2)

    # Before P1
    active_at_4am = timeline.get_active_policies_at(datetime(2026, 9, 1, 4, 0, 0, tzinfo=timezone.utc))
    assert len(active_at_4am) == 0

    # Between P1 and P2 (10 AM)
    active_at_10am = timeline.get_active_policies_at(datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc))
    assert len(active_at_10am) == 1
    assert active_at_10am[0].policy_id == "P001"

    # After P2 (20 PM)
    active_at_20pm = timeline.get_active_policies_at(datetime(2026, 9, 1, 20, 0, 0, tzinfo=timezone.utc))
    assert len(active_at_20pm) == 2


def test_policy_trigger_listener():
    """Tests PolicyTrigger listener notification callbacks."""
    trigger = PolicyTrigger()
    received_policies = []

    def on_policy_triggered(p: PolicyEvent):
        received_policies.append(p)

    trigger.register_listener(on_policy_triggered)

    p = PolicyEvent(
        policy_id="P003",
        policy_name="Trigger Test Policy",
        timestamp=datetime.now(timezone.utc),
        description="Test trigger listener",
    )
    trigger.trigger_policy(p)

    assert len(received_policies) == 1
    assert received_policies[0].policy_id == "P003"


def test_simulator_policy_injection_global_drop():
    """Tests simulator introducing Policy P001 (-20% overall engagement after T0)."""
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    p001 = PolicyEvent(
        policy_id="P001",
        policy_name="Global Drop Policy",
        timestamp=t0,
        description="Global 20% engagement drop",
        impact_factor=0.80,  # 20% event suppression
    )

    timeline = PolicyTimeline()
    timeline.add_policy_event(p001)

    config = EventGeneratorConfig(
        num_users=100,
        num_events=5000,
        seed=42,
        start_time=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
        duration_hours=24.0,
    )

    generator = EventGenerator(config, timeline=timeline)
    events = generator.generate_events()

    pre_policy_events = [e for e in events if e.timestamp < t0]
    post_policy_events = [e for e in events if e.timestamp >= t0]

    # Rates: pre-policy vs post-policy (12 hours each)
    pre_rate = len(pre_policy_events) / 12.0
    post_rate = len(post_policy_events) / 12.0

    # Post rate should be noticeably lower than pre rate due to 20% drop
    assert post_rate < pre_rate
    assert post_policy_events[0].policy_state == "P001"


def test_simulator_policy_injection_target_metric():
    """Tests simulator introducing Policy P003 (affecting comments but leaving likes unchanged)."""
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    p003 = PolicyEvent(
        policy_id="P003",
        policy_name="Comment Suppression Policy",
        timestamp=t0,
        description="Reduces comments by 50% while leaving likes unaffected",
        target_metric=MetricType.COMMENT,
        impact_factor=0.50,
    )

    timeline = PolicyTimeline()
    timeline.add_policy_event(p003)

    config = EventGeneratorConfig(
        num_users=100,
        num_events=5000,
        seed=42,
        start_time=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
        duration_hours=24.0,
    )

    generator = EventGenerator(config, timeline=timeline)
    events = generator.generate_events()

    pre_comments = [e for e in events if e.timestamp < t0 and e.metric_type == MetricType.COMMENT]
    post_comments = [e for e in events if e.timestamp >= t0 and e.metric_type == MetricType.COMMENT]

    pre_likes = [e for e in events if e.timestamp < t0 and e.metric_type == MetricType.LIKE]
    post_likes = [e for e in events if e.timestamp >= t0 and e.metric_type == MetricType.LIKE]

    # Comments drop significantly post-policy
    assert len(post_comments) < len(pre_comments) * 0.7
    # Likes remain stable (ratio post/pre close to ~1.0)
    like_ratio = len(post_likes) / float(len(pre_likes))
    assert 0.85 <= like_ratio <= 1.15
