"""
Unit Tests for HyperLogLog Unique-User Cardinality Estimation.
"""

import pytest
from app.preprocessing.privacy import pseudonymize_user_id
from app.sketches.hyperloglog import HyperLogLog


def test_hll_initialization():
    """Tests HyperLogLog initialization, precision bounds, and memory calculation."""
    hll = HyperLogLog(p=14, seed=42)
    assert hll.p == 14
    assert hll.m == 16384  # 2^14
    assert hll.memory_bytes() == 16384  # uint8 registers = 16 KB
    assert round(hll.expected_relative_error(), 4) == round(1.04 / 128.0, 4)


def test_hll_invalid_precision():
    """Verifies that invalid precision parameter raises ValueError."""
    with pytest.raises(ValueError):
        HyperLogLog(p=3)
        
    with pytest.raises(ValueError):
        HyperLogLog(p=17)


def test_hll_single_and_repeat_adds():
    """Tests that repeating identical items does not increase cardinality estimate."""
    hll = HyperLogLog(p=12, seed=42)
    user_hash = pseudonymize_user_id("user_single")

    for _ in range(500):
        hll.add(user_hash)

    est = hll.estimate()
    # Estimate should be close to 1.0
    assert abs(est - 1.0) <= 0.5


def test_hll_cardinality_accuracy_within_error_bounds():
    """Verifies that cardinality estimate for 5,000 unique items falls within expected error bounds."""
    hll = HyperLogLog(p=14, seed=42)
    exact_count = 5000

    for i in range(exact_count):
        hll.add(pseudonymize_user_id(f"unique_user_{i}"))

    est = hll.estimate()
    rel_error = abs(est - exact_count) / float(exact_count)

    # Standard error for p=14 is ~0.81%; check relative error is well under 3 * SE (2.5%)
    assert rel_error <= 0.03


def test_hll_merge():
    """Tests merging two HyperLogLog sketches populated from distinct item sets."""
    hll1 = HyperLogLog(p=12, seed=42)
    hll2 = HyperLogLog(p=12, seed=42)

    # Add 1,000 users to hll1
    for i in range(1000):
        hll1.add(pseudonymize_user_id(f"user_set_1_{i}"))

    # Add 1,000 users to hll2 (500 overlapping, 500 new -> total 1,500 unique)
    for i in range(500, 1500):
        hll2.add(pseudonymize_user_id(f"user_set_1_{i}"))

    merged = hll1.merge(hll2)
    est_merged = merged.estimate()

    # Exact unique count across sets = 1,500
    rel_error = abs(est_merged - 1500) / 1500.0
    assert rel_error <= 0.05


def test_hll_merge_invalid_precision():
    """Verifies merging sketches with different precision raises ValueError."""
    hll1 = HyperLogLog(p=10)
    hll2 = HyperLogLog(p=12)

    with pytest.raises(ValueError):
        hll1.merge(hll2)


def test_hll_reset():
    """Tests reset operation zeroes out registers."""
    hll = HyperLogLog(p=10)
    hll.add("user_reset")
    assert hll.estimate() > 0.0

    hll.reset()
    assert hll.estimate() == 0.0
    assert (hll.registers == 0).all()


def test_hll_serialization():
    """Tests to_dict and from_dict state serialization."""
    hll = HyperLogLog(p=12, seed=77)
    for i in range(100):
        hll.add(f"item_{i}")

    est_before = hll.estimate()
    serialized = hll.to_dict()

    deserialized = HyperLogLog.from_dict(serialized)
    assert deserialized.p == 12
    assert deserialized.estimate() == est_before
