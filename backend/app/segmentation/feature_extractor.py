"""
Privacy-Safe Behavioral Feature Extraction for Streaming User Segmentation.
"""

from typing import Dict, List, Optional
import numpy as np
from pydantic import BaseModel, Field

from app.ingestion.models import EngagementEvent, MetricType

FEATURE_METRICS: List[MetricType] = [
    MetricType.LIKE,
    MetricType.COMMENT,
    MetricType.SHARE,
    MetricType.CLICK,
    MetricType.VIEW,
]

FEATURE_CATEGORIES: List[str] = [
    "education",
    "news",
    "gaming",
    "lifestyle",
    "technology",
    "entertainment",
]


class UserFeatureVector(BaseModel):
    """Container for a user's privacy-safe behavioral feature vector."""

    user_hash: str = Field(..., description="Pseudonymous SHA-256 user identifier")
    interaction_count: int = Field(default=0, description="Total events")
    session_count: int = Field(default=0, description="Total sessions")
    avg_session_duration: float = Field(default=0.0, description="Average session duration in seconds")
    metric_ratios: Dict[str, float] = Field(default_factory=dict, description="Proportions per metric type")
    category_ratios: Dict[str, float] = Field(default_factory=dict, description="Proportions per topic category")

    def to_numpy(self) -> np.ndarray:
        """
        Converts feature attributes into a normalized 1D float array for clustering.
        
        Vector Layout (Total length = 2 + 5 + 6 = 13 features):
            [0] log1p(interaction_count)
            [1] log1p(avg_session_duration)
            [2..6] metric_ratios (like, comment, share, click, view)
            [7..12] category_ratios (education, news, gaming, lifestyle, technology, entertainment)
        """
        vec = [
            math.log1p(float(self.interaction_count)),
            math.log1p(float(self.avg_session_duration)),
        ]
        
        for m in FEATURE_METRICS:
            vec.append(float(self.metric_ratios.get(m.value, 0.0)))

        for cat in FEATURE_CATEGORIES:
            vec.append(float(self.category_ratios.get(cat, 0.0)))

        return np.array(vec, dtype=np.float64)


import math  # Module import for math.log1p


class UserFeatureExtractor:
    """Extracts privacy-safe behavioral feature vectors from event collections."""

    @classmethod
    def extract_features(cls, events: List[EngagementEvent]) -> Dict[str, UserFeatureVector]:
        """
        Processes a list of events and aggregates per-user behavioral feature vectors.
        
        Args:
            events: List of validated EngagementEvent objects.
            
        Returns:
            Dict mapping user_hash -> UserFeatureVector.
        """
        # User intermediate stats: user_hash -> stats dict
        user_stats: Dict[str, Dict] = {}

        for evt in events:
            u_hash = evt.user_hash
            if u_hash not in user_stats:
                user_stats[u_hash] = {
                    "total_count": 0,
                    "session_count": 0,
                    "durations": [],
                    "metrics": {m.value: 0 for m in MetricType},
                    "categories": {cat: 0 for cat in FEATURE_CATEGORIES},
                }

            st = user_stats[u_hash]
            st["total_count"] += 1

            # Count metric types
            m_val = evt.metric_type.value
            if m_val in st["metrics"]:
                st["metrics"][m_val] += 1

            if evt.metric_type == MetricType.SESSION:
                st["session_count"] += 1
            elif evt.metric_type == MetricType.SESSION_DURATION:
                st["durations"].append(evt.value)

            # Count categories
            cat = evt.content_category.lower()
            if cat in st["categories"]:
                st["categories"][cat] += 1

        # Build UserFeatureVector instances
        result: Dict[str, UserFeatureVector] = {}
        for u_hash, st in user_stats.items():
            tot = max(1, st["total_count"])
            
            m_ratios = {m_name: count / float(tot) for m_name, count in st["metrics"].items()}
            cat_ratios = {cat_name: count / float(tot) for cat_name, count in st["categories"].items()}
            
            avg_dur = float(np.mean(st["durations"])) if st["durations"] else 0.0

            result[u_hash] = UserFeatureVector(
                user_hash=u_hash,
                interaction_count=st["total_count"],
                session_count=st["session_count"],
                avg_session_duration=round(avg_dur, 2),
                metric_ratios={k: round(v, 4) for k, v in m_ratios.items()},
                category_ratios={k: round(v, 4) for k, v in cat_ratios.items()},
            )

        return result
