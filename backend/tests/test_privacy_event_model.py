"""
Unit Tests for Privacy-Safe Event Model and Data Minimization Layer.
"""

from datetime import datetime, timezone
import pytest
from app.core.exceptions import ValidationException
from app.ingestion.models import EngagementEvent, MetricType
from app.preprocessing.privacy import (
    PrivacySanitizer,
    PrivacyViolationException,
    pseudonymize_user_id,
)
from app.preprocessing.validator import EventValidator


def test_valid_engagement_event_creation():
    """Verifies that a valid EngagementEvent payload is successfully instantiated."""
    raw_payload = {
        "event_id": "evt_1001",
        "user_hash": pseudonymize_user_id("user_42"),
        "metric_type": "like",
        "value": 1.0,
        "timestamp": "2026-09-02T10:00:00Z",
        "content_category": "education",
        "segment_metadata": {"session_count": 3},
        "policy_state": "pre_policy",
    }
    
    event = EventValidator.validate_and_parse(raw_payload)
    
    assert event.event_id == "evt_1001"
    assert event.metric_type == MetricType.LIKE
    assert event.value == 1.0
    assert event.content_category == "education"
    assert event.timestamp.tzinfo == timezone.utc


def test_pseudonymize_user_id_determinism():
    """Ensures pseudonymize_user_id produces consistent 64-char hex SHA-256 hashes."""
    hash1 = pseudonymize_user_id("user_abc")
    hash2 = pseudonymize_user_id("user_abc")
    hash3 = pseudonymize_user_id("user_xyz")
    
    assert len(hash1) == 64
    assert hash1 == hash2
    assert hash1 != hash3


def test_rejects_raw_pii_in_user_hash():
    """Verifies that unhashed email addresses or phone numbers are rejected as user_hash."""
    payload_email = {
        "event_id": "evt_1002",
        "user_hash": "user@example.com",  # Raw email!
        "metric_type": "comment",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    with pytest.raises(ValidationException) as exc_info:
        EventValidator.validate_and_parse(payload_email)
    
    assert "Raw PII" in str(exc_info.value)


def test_rejects_forbidden_private_content_fields():
    """Verifies that events containing forbidden private content fields are strictly rejected."""
    forbidden_payload = {
        "event_id": "evt_1003",
        "user_hash": pseudonymize_user_id("user_123"),
        "metric_type": "comment",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message_content": "This is a private message body!",  # Forbidden private field!
    }
    
    with pytest.raises(PrivacyViolationException) as exc_info:
        EventValidator.validate_and_parse(forbidden_payload)
    
    assert "forbidden private fields" in str(exc_info.value)
    assert "message_content" in str(exc_info.value)


def test_rejects_nested_forbidden_fields():
    """Verifies that forbidden fields inside metadata dictionaries are also detected and rejected."""
    nested_forbidden_payload = {
        "event_id": "evt_1004",
        "user_hash": pseudonymize_user_id("user_123"),
        "metric_type": "click",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "segment_metadata": {
            "user_info": {
                "password": "secret_password_123"  # Nested forbidden field!
            }
        },
    }
    
    with pytest.raises(PrivacyViolationException) as exc_info:
        EventValidator.validate_and_parse(nested_forbidden_payload)
    
    assert "segment_metadata.user_info.password" in str(exc_info.value)


def test_rejects_unsupported_metric_type():
    """Verifies that unsupported engagement metric types are rejected."""
    unsupported_metric_payload = {
        "event_id": "evt_1005",
        "user_hash": pseudonymize_user_id("user_123"),
        "metric_type": "unsupported_metric_xyz",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    with pytest.raises(ValidationException) as exc_info:
        EventValidator.validate_and_parse(unsupported_metric_payload)
    
    assert "Unsupported metric_type" in str(exc_info.value)


def test_rejects_negative_metric_value():
    """Verifies that negative metric values are rejected."""
    negative_value_payload = {
        "event_id": "evt_1006",
        "user_hash": pseudonymize_user_id("user_123"),
        "metric_type": "like",
        "value": -5.0,  # Invalid negative value!
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    with pytest.raises(ValidationException):
        EventValidator.validate_and_parse(negative_value_payload)


def test_sanitizer_non_strict_purging():
    """Tests that non-strict sanitizer purges forbidden keys while preserving valid ones."""
    raw_dict = {
        "event_id": "evt_1007",
        "valid_key": "safe_value",
        "email": "user@test.com",
    }
    
    sanitized = PrivacySanitizer.sanitize_event_dict(raw_dict, strict_reject=False)
    
    assert "email" not in sanitized
    assert sanitized["event_id"] == "evt_1007"
    assert sanitized["valid_key"] == "safe_value"
