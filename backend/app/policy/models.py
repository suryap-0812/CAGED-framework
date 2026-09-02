"""
Policy Event Models & Schema Definitions for CAGED Framework.
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.ingestion.models import MetricType
from app.simulation.user_profile import UserSegment


class PolicyEvent(BaseModel):
    """
    Representation of a social-platform policy adjustment event.
    
    CAGED receives only metadata (policy_id, policy_name, timestamp, description).
    The simulator uses target_metric, target_segment, and impact_factor to simulate
    post-policy degradation streams.
    """

    policy_id: str = Field(..., min_length=1, description="Unique policy identifier (e.g. P001)")
    policy_name: str = Field(..., min_length=1, description="Human-readable policy title")
    timestamp: datetime = Field(..., description="UTC timestamp when policy takes effect (T0)")
    description: str = Field(..., description="Detailed description of the policy change")
    
    # Optional targeting parameters used by simulator (not pre-given to detector)
    target_metric: Optional[MetricType] = Field(default=None, description="Target engagement metric if specific")
    target_segment: Optional[UserSegment] = Field(default=None, description="Target user segment if specific")
    target_category: Optional[str] = Field(default=None, description="Target content category if specific")
    impact_factor: float = Field(
        default=0.80, ge=0.0, le=2.0, description="Simulator relative multiplier (e.g. 0.8 = -20% drop)"
    )

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp_utc(cls, v: datetime) -> datetime:
        """Ensures timestamp has UTC timezone information."""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    def to_caged_metadata(self) -> "PolicyMetadata":
        """
        Extracts metadata available to CAGED detection modules (without revealing target ground truth).
        """
        return PolicyMetadata(
            policy_id=self.policy_id,
            policy_name=self.policy_name,
            timestamp=self.timestamp,
            description=self.description,
        )


class PolicyMetadata(BaseModel):
    """Clean metadata passed to CAGED framework without ground-truth answers."""

    policy_id: str
    policy_name: str
    timestamp: datetime
    description: str
