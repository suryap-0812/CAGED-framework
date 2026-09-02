"""
Unit Tests for Metric Engine & Rolling Window Aggregations.
"""

from datetime import datetime, timedelta, timezone
import math
import pytest

from app.ingestion.models import EngagementEvent, MetricType
from app.metrics.aggregator import MetricAggregator
from app.metrics.rolling_window import RollingTimeWindow
from app.preprocessing.privacy import pseudonymize_user_id


def test_exact_small_dataset_calculations():
    """Verifies exact manual calculation of sum, mean, sample variance, stddev, and rates."""
    rw = RollingTimeWindow(metric_type=MetricType.LIKE, window_seconds=300)
    base_time = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)

    # Values: [2.0, 4.0, 6.0]
    # Sum = 12.0, Count = 3
    # Mean = 4.0
    # Sample Variance = ((2-4)^2 + (4-4)^2 + (6-4)^2) / (3-1) = (4 + 0 + 4) / 2 = 4.0
    # StdDev = sqrt(4.0) = 2.0
    # Rate = 12.0 / 300 = 0.04
    rw.add(timestamp=base_time, value=2.0, user_hash=pseudonymize_user_id("u1"))
    rw.add(timestamp=base_time + timedelta(seconds=10), value=4.0, user_hash=pseudonymize_user_id("u2"))
    rw.add(timestamp=base_time + timedelta(seconds=20), value=6.0, user_hash=pseudonymize_user_id("u3"))

    stats = rw.compute_statistics()

    assert stats.count == 3
    assert stats.total_value == 12.0
    assert stats.mean == 4.0
    assert stats.variance == 4.0
    assert stats.std_dev == 2.0
    assert stats.rate_per_sec == 0.04
    assert stats.unique_users_count == 3


def test_rolling_window_sliding_eviction():
    """Verifies that events older than window_seconds are properly evicted when time slides."""
    rw = RollingTimeWindow(metric_type=MetricType.COMMENT, window_seconds=60)
    base_time = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)

    # Add event at T=0
    rw.add(timestamp=base_time, value=1.0, user_hash=pseudonymize_user_id("u1"))
    # Add event at T=30s
    rw.add(timestamp=base_time + timedelta(seconds=30), value=1.0, user_hash=pseudonymize_user_id("u2"))
    
    assert rw.compute_statistics().count == 2

    # Add event at T=65s (causes T=0 event to slide out of 60s window)
    rw.add(timestamp=base_time + timedelta(seconds=65), value=1.0, user_hash=pseudonymize_user_id("u3"))

    stats = rw.compute_statistics()
    assert stats.count == 2  # Events at T=30s and T=65s remain
    assert stats.unique_users_count == 2


def test_zero_observations_and_single_observation():
    """Verifies edge cases: empty window and single-observation window (zero variance)."""
    rw = RollingTimeWindow(metric_type=MetricType.CLICK, window_seconds=300)
    
    # 0 observations
    empty_stats = rw.compute_statistics()
    assert empty_stats.count == 0
    assert empty_stats.total_value == 0.0
    assert empty_stats.mean == 0.0
    assert empty_stats.variance == 0.0
    assert empty_stats.std_dev == 0.0

    # 1 observation
    base_time = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)
    rw.add(timestamp=base_time, value=5.0, user_hash=pseudonymize_user_id("u1"))
    
    single_stats = rw.compute_statistics()
    assert single_stats.count == 1
    assert single_stats.total_value == 5.0
    assert single_stats.mean == 5.0
    assert single_stats.variance == 0.0  # Sample variance requires N > 1
    assert single_stats.std_dev == 0.0


def test_metric_aggregator_multi_window():
    """Tests MetricAggregator across multiple metrics and time windows (1m, 5m, 15m, 1h)."""
    aggregator = MetricAggregator(supported_windows=[60, 300, 900, 3600])
    base_time = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)

    evt1 = EngagementEvent(
        event_id="evt_agg_1",
        user_hash=pseudonymize_user_id("u1"),
        metric_type=MetricType.LIKE,
        value=1.0,
        timestamp=base_time,
    )
    evt2 = EngagementEvent(
        event_id="evt_agg_2",
        user_hash=pseudonymize_user_id("u2"),
        metric_type=MetricType.LIKE,
        value=1.0,
        timestamp=base_time + timedelta(seconds=10),
    )
    evt3 = EngagementEvent(
        event_id="evt_agg_3",
        user_hash=pseudonymize_user_id("u1"),
        metric_type=MetricType.SESSION_DURATION,
        value=120.0,
        timestamp=base_time + timedelta(seconds=20),
    )

    aggregator.update_batch([evt1, evt2, evt3])

    # Check LIKE stats in 5m window (300s)
    like_stats_5m = aggregator.get_statistics(MetricType.LIKE, window_seconds=300)
    assert like_stats_5m.count == 2
    assert like_stats_5m.total_value == 2.0
    assert like_stats_5m.unique_users_count == 2

    # Check SESSION_DURATION stats in 15m window (900s)
    dur_stats_15m = aggregator.get_statistics(MetricType.SESSION_DURATION, window_seconds=900)
    assert dur_stats_15m.count == 1
    assert dur_stats_15m.total_value == 120.0
    assert dur_stats_15m.mean == 120.0

    # Verify get_all_statistics returns entries for all MetricTypes
    all_stats = aggregator.get_all_statistics(window_seconds=300)
    assert len(all_stats) == len(MetricType)
    assert MetricType.LIKE in all_stats
    assert MetricType.SESSION_DURATION in all_stats


def test_boundary_timestamps():
    """Tests boundary condition where event timestamp is exactly at window cutoff."""
    rw = RollingTimeWindow(metric_type=MetricType.VIEW, window_seconds=60)
    base_time = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)

    # Event at T=0
    rw.add(timestamp=base_time, value=1.0, user_hash=pseudonymize_user_id("u1"))
    # Event exactly at T=60s (cutoff = 60s - 60s = 0s, so T=0 is right on boundary)
    rw.add(timestamp=base_time + timedelta(seconds=60), value=1.0, user_hash=pseudonymize_user_id("u2"))

    stats = rw.compute_statistics(reference_time=base_time + timedelta(seconds=60))
    # T=0 event is at cutoff (ref - 60s), boundary check: observations[0][0] < cutoff -> 0s < 0s is False, so kept.
    assert stats.count == 2
