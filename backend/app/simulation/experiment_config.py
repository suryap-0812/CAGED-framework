"""
Experiment and Scenario Configuration Layer for CAGED Simulation Engine.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.simulation.user_profile import UserSegment


class PolicyMechanism(str, Enum):
    """Production-inspired recommendation policy mechanisms."""

    NO_POLICY = "no_policy"
    ORIGINALITY_BOOST = "originality_boost"  # Increases weight on original content score
    SHORT_FORM_RANKING_SHIFT = "short_form_ranking_shift"  # Alters watch-time vs completion weight
    QUALITY_THRESHOLD_RAISE = "quality_threshold_raise"  # Penalizes clickbait/low-quality items
    SURFACE_ALLOCATION_SHIFT = "surface_allocation_shift"  # Reallocates surface impressions


class ExternalDisturbanceType(str, Enum):
    """External time-varying shocks affecting treatment and control cohorts."""

    NONE = "none"
    GLOBAL_OUTAGE = "global_outage"  # Network/platform-wide latency slowdown
    COMPETITOR_SPIKE = "competitor_spike"  # External event driving traffic drop
    DIURNAL_HOLIDAY_NOISE = "diurnal_holiday_noise"  # Natural traffic volume spike


class ExternalDisturbance(BaseModel):
    """Configuration for an external time-varying shock."""

    disturbance_type: ExternalDisturbanceType = Field(default=ExternalDisturbanceType.NONE)
    onset_time: Optional[datetime] = Field(default=None, description="UTC timestamp of disturbance onset")
    duration_minutes: float = Field(default=60.0, ge=0.0, description="Duration in minutes")
    magnitude: float = Field(default=0.80, description="Multiplier effect on overall activity (e.g. 0.80 = 20% drop)")
    affects_control: bool = Field(default=True, description="SUTVA assumption: common shock affects both cohorts")


class PolicyParameters(BaseModel):
    """Configurable weights and parameters for a policy mechanism."""

    affinity_weight_shift: float = Field(default=0.0, description="Change in user-content affinity weight")
    originality_weight_shift: float = Field(default=0.0, description="Change in originality score weight")
    quality_weight_shift: float = Field(default=0.0, description="Change in content quality score weight")
    freshness_weight_shift: float = Field(default=0.0, description="Change in freshness decay weight")
    promotional_penalty_shift: float = Field(default=0.0, description="Change in promotional item penalty")
    target_segment: Optional[UserSegment] = Field(default=None, description="Optional targeted user segment")
    target_category: Optional[str] = Field(default=None, description="Optional targeted content category")


class ExperimentConfig(BaseModel):
    """Configuration for a scientific synthetic experiment."""

    seed: int = Field(default=42, description="Random seed for 100% reproducible stream generation")
    num_users: int = Field(default=1000, ge=10, description="Total synthetic user population")
    num_items: int = Field(default=500, ge=10, description="Total content item catalog size")
    num_events: Optional[int] = Field(default=None, ge=1, description="Optional total nominal events override")
    event_rate: int = Field(default=1000, ge=10, description="Target events per minute")
    treatment_ratio: float = Field(default=0.50, ge=0.0, le=1.0, description="A/B treatment cohort ratio (0.50 = 50/50)")
    
    start_time: datetime = Field(
        default_factory=lambda: datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
        description="Stream start timestamp",
    )
    t0: Optional[datetime] = Field(default=None, description="Intervention onset timestamp T0")
    t1: Optional[datetime] = Field(default=None, description="Optional policy rollback timestamp T1")
    duration_hours: float = Field(default=24.0, gt=0.0, description="Total experiment duration in hours")
    
    policy_mechanism: PolicyMechanism = Field(default=PolicyMechanism.NO_POLICY)
    policy_params: PolicyParameters = Field(default_factory=PolicyParameters)
    external_disturbance: ExternalDisturbance = Field(default_factory=ExternalDisturbance)
    
    # Practical significance threshold
    minimum_effect_size: float = Field(
        default=0.05,
        ge=0.0,
        description="Practical effect threshold Delta_min (e.g. 0.05 = 5% relative shift)",
    )
