"""
User Behavioral Profiles for Synthetic Social Platform Event Simulator.
"""

from enum import Enum
import random
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.ingestion.models import MetricType
from app.preprocessing.privacy import pseudonymize_user_id


class UserSegment(str, Enum):
    """User behavioral segment classifications."""

    CASUAL = "casual"
    REGULAR = "regular"
    HEAVY = "heavy"
    CONTENT_FOCUSED = "content_focused"


# Default metric weight distributions per behavioral segment
SEGMENT_METRIC_WEIGHTS: Dict[UserSegment, Dict[MetricType, float]] = {
    UserSegment.CASUAL: {
        MetricType.VIEW: 0.65,
        MetricType.LIKE: 0.20,
        MetricType.CLICK: 0.10,
        MetricType.SESSION: 0.03,
        MetricType.SESSION_DURATION: 0.01,
        MetricType.COMMENT: 0.008,
        MetricType.SHARE: 0.002,
    },
    UserSegment.REGULAR: {
        MetricType.VIEW: 0.45,
        MetricType.LIKE: 0.25,
        MetricType.CLICK: 0.15,
        MetricType.COMMENT: 0.08,
        MetricType.SHARE: 0.03,
        MetricType.SESSION: 0.02,
        MetricType.SESSION_DURATION: 0.02,
    },
    UserSegment.HEAVY: {
        MetricType.VIEW: 0.30,
        MetricType.LIKE: 0.25,
        MetricType.COMMENT: 0.20,
        MetricType.SHARE: 0.12,
        MetricType.CLICK: 0.08,
        MetricType.SESSION: 0.03,
        MetricType.SESSION_DURATION: 0.02,
    },
    UserSegment.CONTENT_FOCUSED: {
        MetricType.VIEW: 0.40,
        MetricType.SESSION_DURATION: 0.25,
        MetricType.CLICK: 0.15,
        MetricType.LIKE: 0.10,
        MetricType.COMMENT: 0.06,
        MetricType.SHARE: 0.03,
        MetricType.SESSION: 0.01,
    },
}

# Relative overall activity weights per segment
SEGMENT_ACTIVITY_WEIGHTS: Dict[UserSegment, float] = {
    UserSegment.CASUAL: 0.5,
    UserSegment.REGULAR: 1.0,
    UserSegment.HEAVY: 3.5,
    UserSegment.CONTENT_FOCUSED: 2.0,
}


class UserProfile(BaseModel):
    """Synthetic privacy-safe user profile."""

    user_id: str = Field(..., description="Synthetic internal user ID")
    user_hash: str = Field(..., description="SHA-256 pseudonymous hash")
    segment: UserSegment = Field(..., description="Behavioral segment category")
    preferred_categories: List[str] = Field(default_factory=list, description="Favored content categories")
    activity_weight: float = Field(default=1.0, ge=0.0, description="Event generation probability weight")
    metric_weights: Dict[MetricType, float] = Field(default_factory=dict, description="Metric probabilities")


def create_synthetic_user_profile(
    user_index: int,
    segment: UserSegment,
    available_categories: List[str],
    rng: Optional[random.Random] = None,
) -> UserProfile:
    """
    Generates a synthetic UserProfile.
    
    Args:
        user_index: Integer index for generating user ID.
        segment: Behavioral segment assignment.
        available_categories: List of content topics.
        rng: Python random.Random instance for seed-controlled generation.
        
    Returns:
        UserProfile instance.
    """
    r = rng or random.Random()
    raw_user_id = f"synth_user_{user_index:06d}"
    user_hash = pseudonymize_user_id(raw_user_id)

    # Select 1 to 3 preferred categories for the user
    num_categories = min(len(available_categories), r.randint(1, 3))
    preferred_cats = r.sample(available_categories, k=num_categories)

    # Fetch segment defaults
    base_metric_weights = SEGMENT_METRIC_WEIGHTS[segment]
    base_activity = SEGMENT_ACTIVITY_WEIGHTS[segment]

    # Add slight random perturbation to individual user metric weights (+/- 10%)
    perturbed_weights: Dict[MetricType, float] = {}
    total_w = 0.0
    for m, w in base_metric_weights.items():
        val = max(0.001, w * r.uniform(0.9, 1.1))
        perturbed_weights[m] = val
        total_w += val

    # Normalize perturbed weights
    normalized_weights = {m: w / total_w for m, w in perturbed_weights.items()}

    return UserProfile(
        user_id=raw_user_id,
        user_hash=user_hash,
        segment=segment,
        preferred_categories=preferred_cats,
        activity_weight=base_activity * r.uniform(0.85, 1.15),
        metric_weights=normalized_weights,
    )
