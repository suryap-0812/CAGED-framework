"""
Production-Inspired Recommendation Ranking Engine for CAGED Platform Simulation.
Modulates candidate item scores post-T0 via production-inspired mechanisms while preserving SUTVA no-interference.
"""

import copy
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.simulation.content_catalog import ContentItem
from app.simulation.experiment_config import PolicyMechanism, PolicyParameters
from app.simulation.user_profile import UserProfile


class RankingWeights(BaseModel):
    """Weights governing the platform's content recommendation scoring function."""

    affinity_weight: float = Field(default=0.40, description="Weight on user-content category affinity")
    originality_weight: float = Field(default=0.25, description="Weight on content originality score")
    quality_weight: float = Field(default=0.25, description="Weight on inherent content quality score")
    freshness_weight: float = Field(default=0.10, description="Weight on item freshness")
    promotional_penalty: float = Field(default=0.15, description="Penalty for promotional items")


class RecommendationEngine:
    """
    Production-inspired recommendation ranking engine.
    Computes candidate item scores: Score(u, c) = w1*Affinity + w2*Originality + w3*Quality + w4*Freshness - w5*Penalty
    """

    def __init__(self, base_weights: Optional[RankingWeights] = None):
        self.base_weights = base_weights or RankingWeights()

    def get_cohort_ranking_weights(
        self,
        is_treatment: bool,
        is_post_t0: bool,
        mechanism: PolicyMechanism,
        params: PolicyParameters,
    ) -> RankingWeights:
        """
        Calculates cohort-specific ranking weights post-T0 while satisfying SUTVA no-interference.
        Treatment-side policy changes NEVER modify control-side ranking weights.
        """
        # Control cohort is ALWAYS governed by base weights (SUTVA assumption)
        if not is_treatment or not is_post_t0 or mechanism == PolicyMechanism.NO_POLICY:
            return copy.deepcopy(self.base_weights)

        w = copy.deepcopy(self.base_weights)

        if mechanism == PolicyMechanism.ORIGINALITY_BOOST:
            # Demotes unoriginal/re-uploaded content by boosting originality weight w2
            w.originality_weight += params.originality_weight_shift or 0.35
            w.affinity_weight = max(0.05, w.affinity_weight - 0.15)
        elif mechanism == PolicyMechanism.SHORT_FORM_RANKING_SHIFT:
            # Shifts focus from category affinity to watch completion / freshness
            w.freshness_weight += params.freshness_weight_shift or 0.25
            w.affinity_weight = max(0.10, w.affinity_weight - 0.20)
        elif mechanism == PolicyMechanism.QUALITY_THRESHOLD_RAISE:
            # Increases penalty on low quality / clickbait
            w.quality_weight += params.quality_weight_shift or 0.30
            w.promotional_penalty += params.promotional_penalty_shift or 0.25
        elif mechanism == PolicyMechanism.SURFACE_ALLOCATION_SHIFT:
            w.affinity_weight += params.affinity_weight_shift or 0.10
            w.freshness_weight = max(0.02, w.freshness_weight - 0.05)

        return w

    def score_item(
        self,
        user: UserProfile,
        item: ContentItem,
        weights: RankingWeights,
    ) -> float:
        """
        Calculates ranking score for a user-item pair based on active ranking weights.
        """
        # Category affinity: 1.0 if category in user preferred_categories, else 0.3
        affinity = 1.0 if item.category in user.preferred_categories else 0.30

        score = (
            weights.affinity_weight * affinity
            + weights.originality_weight * item.originality_score
            + weights.quality_weight * item.quality_score
            + weights.freshness_weight * 0.85  # Freshness assumption
        )

        if item.is_promotional:
            score -= weights.promotional_penalty

        return max(0.0, score)

    def rank_candidates(
        self,
        user: UserProfile,
        candidates: List[ContentItem],
        is_treatment: bool,
        is_post_t0: bool,
        mechanism: PolicyMechanism,
        params: PolicyParameters,
        top_k: int = 5,
    ) -> List[ContentItem]:
        """
        Scores and ranks candidate items for exposure to the user.
        """
        weights = self.get_cohort_ranking_weights(is_treatment, is_post_t0, mechanism, params)
        scored = [(item, self.score_item(user, item, weights)) for item in candidates]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [pair[0] for pair in scored[:top_k]]
