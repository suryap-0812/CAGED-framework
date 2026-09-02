"""
Baseline Snapshot Models for Pre-Policy Counterfactual Freezing.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.ingestion.models import MetricType


class BaselineSnapshot(BaseModel):
    """
    Immutable snapshot of a baseline model state frozen at policy trigger time T0.
    
    Serves as the un-contaminated counterfactual reference for post-policy degradation detection.
    """

    snapshot_id: str = Field(..., description="Unique snapshot identifier")
    policy_id: str = Field(..., description="Associated policy identifier (e.g. P001)")
    metric_type: MetricType = Field(..., description="Target metric type")
    frozen_at: datetime = Field(..., description="UTC timestamp T0 when frozen")
    model_type: str = Field(..., description="Type of baseline model (exponential_smoothing / arima)")
    model_state: Dict[str, Any] = Field(..., description="Serialized baseline parameters at T0")
    segment: Optional[str] = Field(default=None, description="User segment if segment-specific")

    @classmethod
    def create_snapshot_id(cls, policy_id: str, metric_type: MetricType, segment: Optional[str] = None) -> str:
        seg_suffix = f"_{segment}" if segment else ""
        return f"snap_{policy_id}_{metric_type.value}{seg_suffix}"
