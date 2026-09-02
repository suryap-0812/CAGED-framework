"""
Unit Tests for Count-Min Sketch Frequency Estimation.
"""

import pytest
from app.sketches.count_min_sketch import CountMinSketch


def test_cms_initialization():
    """Tests explicit width/depth initialization and epsilon/delta bounds calculation."""
    cms = CountMinSketch(width=500, depth=5, seed=42)
    assert cms.width == 500
    assert cms.depth == 5
    assert cms.total_count == 0.0
    assert cms.memory_bytes() == 500 * 5 * 8  # float64 = 8 bytes per cell = 20,000 bytes


def test_cms_init_by_error_bounds():
    """Tests initialization using epsilon and delta error bounds."""
    cms = CountMinSketch(epsilon=0.01, delta=0.01, seed=42)
    assert cms.width > 200
    assert cms.depth >= 4


def test_cms_exact_count_single_key():
    """Tests frequency estimation when only a single key is inserted (zero collisions)."""
    cms = CountMinSketch(width=1000, depth=5, seed=42)
    cms.update("user_alpha", 15.0)
    
    assert cms.estimate("user_alpha") == 15.0
    assert cms.estimate("non_existent_key") == 0.0
    assert cms.total_count == 15.0


def test_cms_never_underestimates():
    """Verifies fundamental property: Count-Min Sketch estimate is always >= exact count."""
    cms = CountMinSketch(width=200, depth=4, seed=123)
    
    counts = {
        "item_a": 100,
        "item_b": 50,
        "item_c": 10,
        "item_d": 1,
    }
    
    for item, freq in counts.items():
        cms.update(item, float(freq))
        
    for item, exact_freq in counts.items():
        est = cms.estimate(item)
        assert est >= exact_freq, f"Estimate {est} was below exact count {exact_freq} for {item}"


def test_cms_reset():
    """Tests reset operation clears the sketch matrix and counters."""
    cms = CountMinSketch(width=100, depth=3)
    cms.update("item_x", 42.0)
    assert cms.estimate("item_x") == 42.0

    cms.reset()
    assert cms.estimate("item_x") == 0.0
    assert cms.total_count == 0.0


def test_cms_serialization():
    """Tests serialization to dictionary and deserialization back to CountMinSketch."""
    cms = CountMinSketch(width=300, depth=4, seed=99)
    cms.update("key_1", 10.0)
    cms.update("key_2", 25.0)

    serialized = cms.to_dict()
    assert serialized["width"] == 300
    assert serialized["depth"] == 4
    assert serialized["total_count"] == 35.0

    deserialized = CountMinSketch.from_dict(serialized)
    assert deserialized.width == 300
    assert deserialized.depth == 4
    assert deserialized.estimate("key_1") == 10.0
    assert deserialized.estimate("key_2") == 25.0
    assert deserialized.total_count == 35.0


def test_cms_error_bound_property():
    """
    Verifies theoretical error bound property:
    estimate(x) <= exact_count(x) + epsilon * total_count.
    """
    cms = CountMinSketch(epsilon=0.05, delta=0.01, seed=42)
    
    # Insert 1,000 items with Zipfian distribution
    exact_counts = {}
    for i in range(1000):
        key = f"key_{i % 50}"
        exact_counts[key] = exact_counts.get(key, 0) + 1
        cms.update(key, 1.0)

    violations = 0
    total_keys = len(exact_counts)

    for key, exact in exact_counts.items():
        est = cms.estimate(key)
        upper_bound = exact + cms.epsilon * cms.total_count
        if est > upper_bound:
            violations += 1

    # Failure rate should be <= delta (0.01)
    failure_rate = violations / float(total_keys)
    assert failure_rate <= cms.delta
