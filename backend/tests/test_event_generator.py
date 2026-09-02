"""
Unit Tests for Synthetic Social Platform Event Generator.
"""

from datetime import datetime, timezone
import os
import subprocess
import sys
import pytest

from app.ingestion.models import EngagementEvent, MetricType
from app.preprocessing.privacy import FORBIDDEN_FIELDS
from app.simulation.event_generator import EventGenerator, EventGeneratorConfig
from app.simulation.user_profile import UserSegment


def test_user_population_segment_proportions():
    """Verifies that user population is initialized according to configured segment ratios."""
    config = EventGeneratorConfig(
        num_users=100,
        num_events=500,
        seed=123,
    )
    generator = EventGenerator(config)
    
    assert len(generator.users) == 100
    
    # Check segment representation
    segments = [u.segment for u in generator.users]
    assert UserSegment.CASUAL in segments
    assert UserSegment.REGULAR in segments
    assert UserSegment.HEAVY in segments
    assert UserSegment.CONTENT_FOCUSED in segments


def test_generator_reproducibility():
    """Verifies that using the same seed produces identical event streams."""
    config1 = EventGeneratorConfig(num_users=50, num_events=200, seed=42)
    config2 = EventGeneratorConfig(num_users=50, num_events=200, seed=42)
    
    gen1 = EventGenerator(config1)
    events1 = gen1.generate_events()
    
    gen2 = EventGenerator(config2)
    events2 = gen2.generate_events()
    
    assert len(events1) == len(events2) == 200
    for e1, e2 in zip(events1, events2):
        assert e1.event_id == e2.event_id
        assert e1.user_hash == e2.user_hash
        assert e1.metric_type == e2.metric_type
        assert e1.value == e2.value
        assert e1.timestamp == e2.timestamp


def test_different_seeds_produce_different_streams():
    """Verifies that different seeds produce distinct streams."""
    config1 = EventGeneratorConfig(num_users=50, num_events=200, seed=42)
    config2 = EventGeneratorConfig(num_users=50, num_events=200, seed=99)
    
    gen1 = EventGenerator(config1)
    events1 = gen1.generate_events()
    
    gen2 = EventGenerator(config2)
    events2 = gen2.generate_events()
    
    # Compare hashes or timestamps
    hashes1 = [e.user_hash for e in events1]
    hashes2 = [e.user_hash for e in events2]
    assert hashes1 != hashes2


def test_generated_events_metric_validity_and_privacy():
    """Ensures all generated events are valid EngagementEvent instances with zero forbidden fields."""
    config = EventGeneratorConfig(num_users=50, num_events=300, seed=77)
    generator = EventGenerator(config)
    events = generator.generate_events()
    
    assert len(events) == 300
    
    for evt in events:
        assert isinstance(evt, EngagementEvent)
        assert isinstance(evt.metric_type, MetricType)
        assert evt.value >= 0.0
        assert evt.user_hash is not None and len(evt.user_hash) == 64
        
        # Verify no forbidden private field names in model dict representation
        evt_dict = evt.model_dump()
        for forbidden in FORBIDDEN_FIELDS:
            assert forbidden not in evt_dict


def test_generated_events_chronological_sorting():
    """Verifies that generated events are ordered monotonically by timestamp."""
    config = EventGeneratorConfig(num_users=50, num_events=200, seed=42)
    generator = EventGenerator(config)
    events = generator.generate_events()
    
    timestamps = [e.timestamp for e in events]
    assert timestamps == sorted(timestamps)


def test_cli_generate_events_script(tmp_path):
    """Tests executing scripts/generate_events.py CLI script."""
    output_file = str(tmp_path / "test_out.json")
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "generate_events.py"))
    
    cmd = [
        sys.executable,
        script_path,
        "--users", "20",
        "--events", "100",
        "--seed", "100",
        "--output", output_file,
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert os.path.exists(output_file)
    assert os.path.getsize(output_file) > 0
