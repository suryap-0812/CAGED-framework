"""
User Behavioral Emergence Engine for CAGED Platform Simulation.
Models the explicit causal chain:
Policy -> Ranking -> Item Exposure/Impression -> User Viewing Behavior -> Watch Completion -> Likes/Comments/Shares/Sessions
"""

import random
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.ingestion.models import MetricType
from app.simulation.content_catalog import ContentItem
from app.simulation.user_profile import UserProfile


class ItemImpression(BaseModel):
    """Represents an explicit content item exposure / impression to a user."""

    user_id: str
    item_id: str
    category: str
    quality_score: float
    originality_score: float
    is_preferred_category: bool
    relevance_score: float  # Combined user relevance


class UserBehaviorOutcome(BaseModel):
    """Emergent behavioral outcome resulting from an item exposure."""

    watch_completion_fraction: float = Field(..., ge=0.0, le=1.0, description="Fraction of item watched (0.0 to 1.0)")
    watch_time_seconds: float = Field(..., ge=0.0, description="Actual seconds watched")
    liked: bool = Field(default=False, description="Did user like the item?")
    commented: bool = Field(default=False, description="Did user comment?")
    shared: bool = Field(default=False, description="Did user share?")
    clicked: bool = Field(default=False, description="Did user click related links?")
    session_continued: bool = Field(default=True, description="Did user continue session or abandon?")


class UserBehaviorModel:
    """
    Translates explicit item exposures / impressions into watch completion and emergent engagement metrics.
    Engagement drops emerge mechanistically from reduced relevance or quality.
    """

    def __init__(self, rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()

    def process_impression(
        self,
        user: UserProfile,
        item: ContentItem,
        rng: Optional[random.Random] = None,
    ) -> UserBehaviorOutcome:
        """
        Processes an item impression and determines watch completion and emergent actions.
        """
        r = rng or self.rng

        is_pref = item.category in user.preferred_categories
        affinity = 1.0 if is_pref else 0.35

        # Watch Completion is driven by item quality and user relevance
        expected_completion = (0.50 * affinity + 0.50 * item.quality_score)
        
        # Originality bonus: Users spend slightly longer on original content
        if item.originality_score > 0.70:
            expected_completion += 0.10

        actual_completion = min(1.0, max(0.05, r.gauss(expected_completion, 0.15)))
        watch_time_sec = round(actual_completion * 180.0, 1)  # 3-minute nominal item length

        # Emergent Action Probabilities (Driven by watch completion and user segment profile)
        # 1. Like Probability: Highly correlated with completion (> 60% completion)
        like_prob = 0.35 * actual_completion * (1.2 if is_pref else 0.6)
        liked = r.random() < like_prob

        # 2. Comment Probability: Requires high completion (> 70%) and user propensity
        comment_prob = 0.15 * (actual_completion ** 2) * (user.metric_weights.get(MetricType.COMMENT, 0.05) / 0.10)
        commented = r.random() < comment_prob

        # 3. Share Probability: Requires high originality + high completion
        share_prob = 0.10 * actual_completion * item.originality_score
        shared = r.random() < share_prob

        # 4. Click Probability: Driven by interest and promotional context
        click_prob = 0.12 * affinity
        clicked = r.random() < click_prob

        # 5. Session Continuation: If watch completion < 20%, high chance of early session abandonment
        session_continued = True if actual_completion >= 0.20 else (r.random() < 0.40)

        return UserBehaviorOutcome(
            watch_completion_fraction=round(actual_completion, 3),
            watch_time_seconds=watch_time_sec,
            liked=liked,
            commented=commented,
            shared=shared,
            clicked=clicked,
            session_continued=session_continued,
        )
