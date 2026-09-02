"""
Synthetic Social Platform Event Generator Engine for CAGED.
"""

from datetime import datetime, timedelta, timezone
import math
import random
from typing import Dict, List, Optional
import numpy as np
from pydantic import BaseModel, Field

from app.ingestion.models import EngagementEvent, MetricType
from app.preprocessing.validator import EventValidator
from app.simulation.user_profile import (
    UserProfile,
    UserSegment,
    create_synthetic_user_profile,
)

DEFAULT_CATEGORIES: List[str] = [
    "education",
    "news",
    "gaming",
    "lifestyle",
    "technology",
    "entertainment",
]


class EventGeneratorConfig(BaseModel):
    """Configuration parameters for synthetic event generation."""

    num_users: int = Field(default=1000, ge=1, description="Total synthetic users")
    num_events: int = Field(default=10000, ge=1, description="Total events to generate")
    seed: int = Field(default=42, description="Random seed for reproducibility")
    start_time: datetime = Field(
        default_factory=lambda: datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
        description="Stream start timestamp",
    )
    duration_hours: float = Field(default=24.0, gt=0.0, description="Time span duration in hours")
    segment_proportions: Dict[UserSegment, float] = Field(
        default_factory=lambda: {
            UserSegment.CASUAL: 0.50,
            UserSegment.REGULAR: 0.30,
            UserSegment.HEAVY: 0.10,
            UserSegment.CONTENT_FOCUSED: 0.10,
        },
        description="Segment population ratios",
    )
    categories: List[str] = Field(default_factory=lambda: DEFAULT_CATEGORIES.copy())


class EventGenerator:
    """Core simulation engine generating privacy-safe engagement events."""

    def __init__(self, config: EventGeneratorConfig):
        self.config = config
        self.py_rng = random.Random(config.seed)
        self.np_rng = np.random.default_rng(config.seed)
        self.users: List[UserProfile] = []
        self._init_user_population()

    def _init_user_population(self) -> None:
        """Instantiates synthetic user population across configured segment proportions."""
        total_users = self.config.num_users
        proportions = self.config.segment_proportions
        
        # Calculate counts per segment
        counts: Dict[UserSegment, int] = {}
        allocated = 0
        segments = list(proportions.keys())
        
        for seg in segments[:-1]:
            c = int(total_users * proportions[seg])
            counts[seg] = c
            allocated += c
        counts[segments[-1]] = max(0, total_users - allocated)

        # Build user objects
        user_idx = 0
        for seg, count in counts.items():
            for _ in range(count):
                u = create_synthetic_user_profile(
                    user_index=user_idx,
                    segment=seg,
                    available_categories=self.config.categories,
                    rng=self.py_rng,
                )
                self.users.append(u)
                user_idx += 1

        # Precompute user selection probability weights
        self.user_weights = np.array([u.activity_weight for u in self.users], dtype=np.float64)
        self.user_weights /= self.user_weights.sum()

    def _diurnal_time_shift(self, event_index: int, total_events: int) -> float:
        """
        Calculates time offset (in seconds) introducing a diurnal (day/night) sinusoidal activity pattern.
        """
        total_duration_sec = self.config.duration_hours * 3600.0
        # Non-uniform time distribution using cumulative distribution function sampling
        u = (event_index + self.np_rng.uniform(0, 1)) / float(total_events)
        
        # Superimpose sinusoidal diurnal variation (peak at 14:00, trough at 04:00)
        # Base uniform progression + sinusoidal shift
        base_sec = u * total_duration_sec
        hour_of_day = (base_sec / 3600.0) % 24.0
        
        # Sinusoidal modifier: higher event density during peak hours
        diurnal_factor = 0.3 * math.sin((hour_of_day - 8.0) * math.pi / 12.0)
        adjusted_sec = max(0.0, min(total_duration_sec, base_sec + diurnal_factor * 1800.0))
        
        return adjusted_sec

    def generate_events(self, policy_state: str = "pre_policy") -> List[EngagementEvent]:
        """
        Generates deterministic stream of validated EngagementEvent objects.
        
        Args:
            policy_state: Operational policy flag ("pre_policy" or "post_policy").
            
        Returns:
            List of valid EngagementEvent instances sorted by timestamp.
        """
        events: List[EngagementEvent] = []
        total_events = self.config.num_events
        start_time = self.config.start_time

        # Sample user selections in bulk
        selected_user_indices = self.np_rng.choice(
            len(self.users), size=total_events, p=self.user_weights
        )

        for i in range(total_events):
            user = self.users[selected_user_indices[i]]
            
            # Select metric based on user's metric weights
            metric_types = list(user.metric_weights.keys())
            metric_probs = list(user.metric_weights.values())
            selected_metric_str = self.py_rng.choices(metric_types, weights=metric_probs, k=1)[0]
            metric_enum = MetricType(selected_metric_str)

            # Assign realistic metric value
            if metric_enum == MetricType.SESSION_DURATION:
                # Log-normal distribution for session duration (e.g. 30s to 1200s)
                val = float(round(self.np_rng.lognormal(mean=4.5, sigma=0.8), 2))
                val = max(5.0, val)
            else:
                val = 1.0

            # Select content category (prefer user's favorite categories 80% of the time)
            if user.preferred_categories and self.py_rng.random() < 0.8:
                cat = self.py_rng.choice(user.preferred_categories)
            else:
                cat = self.py_rng.choice(self.config.categories)

            # Compute timestamp with diurnal shift
            offset_sec = self._diurnal_time_shift(i, total_events)
            evt_time = start_time + timedelta(seconds=offset_sec)

            raw_dict = {
                "event_id": f"evt_{i+1:08d}",
                "user_hash": user.user_hash,
                "metric_type": metric_enum.value,
                "value": val,
                "timestamp": evt_time.isoformat(),
                "content_category": cat,
                "segment_metadata": {
                    "user_segment": user.segment.value,
                },
                "policy_state": policy_state,
            }

            # Enforce strict privacy and schema validation
            event = EventValidator.validate_and_parse(raw_dict)
            events.append(event)

        # Sort events by timestamp to ensure chronological stream ordering
        events.sort(key=lambda e: e.timestamp)
        return events
