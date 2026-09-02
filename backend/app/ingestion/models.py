"""
Canonical Engagement Event Data Model for CAGED.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class MetricType(str, Enum):
    """Supported privacy-safe behavioral engagement metrics."""

    LIKE = "like"
    COMMENT = "comment"
    SHARE = "share"
    CLICK = "click"
    SESSION = "session"
    SESSION_DURATION = "session_duration"
    VIEW = "view"


class EngagementEvent(BaseModel):
    """
    Canonical privacy-safe engagement event representation.
    
    Attributes:
        event_id: Unique string identifier for the event.
        user_hash: SHA-256 pseudonymous identifier representing the user.
        metric_type: Standardized engagement metric type.
        value: Numerical value associated with the event (e.g. 1.0 for like, 120.5 for duration).
        timestamp: Time of event occurrence in UTC.
        content_category: Coarse, non-private topic category (e.g. education, news).
        segment_metadata: Optional dictionary containing non-private behavioral telemetry features.
        policy_state: Operational state identifier ("pre_policy" or "post_policy").
    """

    event_id: str = Field(..., min_length=1, description="Unique event identifier")
    user_hash: str = Field(..., min_length=16, description="Pseudonymous SHA-256 user hash")
    metric_type: MetricType = Field(..., description="Privacy-safe metric category")
    value: float = Field(default=1.0, ge=0.0, description="Quantitative metric value")
    timestamp: datetime = Field(..., description="UTC timestamp of the event")
    content_category: str = Field(default="general", min_length=1, description="Non-private category label")
    segment_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Behavioral metadata")
    policy_state: Optional[str] = Field(default="pre_policy", description="Policy state flag")

    @field_validator("user_hash")
    @classmethod
    def validate_user_hash_format(cls, v: str) -> str:
        """Ensures user_hash does not resemble unhashed PII like an email address or raw phone number."""
        v_strip = v.strip().lower()
        if "@" in v_strip or v_strip.startswith("+") or " " in v_strip:
            raise ValueError("Raw PII (email, phone number, or name) cannot be used as user_hash. Must be pseudonymized.")
        return v_strip

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp_utc(cls, v: datetime) -> datetime:
        """Ensures timestamp has UTC timezone information."""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @model_validator(mode="before")
    @classmethod
    def enforce_metric_type_compatibility(cls, data: Any) -> Any:
        """Validates metric type string compatibility before field parsing."""
        if isinstance(data, dict):
            metric_val = data.get("metric_type")
            if isinstance(metric_val, str):
                valid_metrics = [m.value for m in MetricType]
                if metric_val.lower() not in valid_metrics:
                    raise ValueError(f"Unsupported metric_type '{metric_val}'. Allowed: {valid_metrics}")
                data["metric_type"] = metric_val.lower()
        return data
