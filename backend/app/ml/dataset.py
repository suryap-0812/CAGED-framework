"""
Feature Dataset Builder for Optional Early-Warning ML Degradation Predictor.
"""

from datetime import datetime, timezone
import math
from typing import Dict, List, Optional, Tuple
import numpy as np
from pydantic import BaseModel, Field

from app.ingestion.models import MetricType

ML_FEATURE_NAMES: List[str] = [
    "like_mean_5m",
    "like_z_score",
    "like_rate_of_change",
    "comment_mean_5m",
    "comment_z_score",
    "comment_rate_of_change",
    "share_mean_5m",
    "share_z_score",
    "share_rate_of_change",
    "composite_s_score",
    "micro_variance_ratio",
    "diurnal_sin",
    "diurnal_cos",
]


class MLFeatureVector(BaseModel):
    """Container for an early-warning ML feature vector at timestamp t."""

    timestamp: datetime = Field(..., description="UTC timestamp of feature extraction")
    like_mean_5m: float = Field(default=0.0)
    like_z_score: float = Field(default=0.0)
    like_rate_of_change: float = Field(default=0.0)
    comment_mean_5m: float = Field(default=0.0)
    comment_z_score: float = Field(default=0.0)
    comment_rate_of_change: float = Field(default=0.0)
    share_mean_5m: float = Field(default=0.0)
    share_z_score: float = Field(default=0.0)
    share_rate_of_change: float = Field(default=0.0)
    composite_s_score: float = Field(default=0.0)
    micro_variance_ratio: float = Field(default=1.0)
    diurnal_sin: float = Field(default=0.0)
    diurnal_cos: float = Field(default=1.0)

    def to_numpy(self) -> np.ndarray:
        """Converts feature attributes to 1D float array."""
        return np.array(
            [
                self.like_mean_5m,
                self.like_z_score,
                self.like_rate_of_change,
                self.comment_mean_5m,
                self.comment_z_score,
                self.comment_rate_of_change,
                self.share_mean_5m,
                self.share_z_score,
                self.share_rate_of_change,
                self.composite_s_score,
                self.micro_variance_ratio,
                self.diurnal_sin,
                self.diurnal_cos,
            ],
            dtype=np.float64,
        )


class MLFeatureDatasetBuilder:
    """Builds early-warning ML feature vectors and target labels from metric streams."""

    @classmethod
    def build_feature_vector(
        self,
        timestamp: datetime,
        metric_means: Dict[MetricType, float],
        metric_z_scores: Dict[MetricType, float],
        metric_rates_of_change: Dict[MetricType, float],
        composite_s_score: float,
        micro_variance_ratio: float = 1.0,
    ) -> MLFeatureVector:
        """Constructs a single MLFeatureVector instance from stream snapshots."""
        t_utc = timestamp if timestamp.tzinfo is not None else timestamp.replace(tzinfo=timezone.utc)
        
        # Diurnal cyclical time features
        hour_val = t_utc.hour + (t_utc.minute / 60.0)
        sin_t = math.sin(2.0 * math.pi * hour_val / 24.0)
        cos_t = math.cos(2.0 * math.pi * hour_val / 24.0)

        return MLFeatureVector(
            timestamp=t_utc,
            like_mean_5m=round(metric_means.get(MetricType.LIKE, 0.0), 4),
            like_z_score=round(metric_z_scores.get(MetricType.LIKE, 0.0), 4),
            like_rate_of_change=round(metric_rates_of_change.get(MetricType.LIKE, 0.0), 4),
            comment_mean_5m=round(metric_means.get(MetricType.COMMENT, 0.0), 4),
            comment_z_score=round(metric_z_scores.get(MetricType.COMMENT, 0.0), 4),
            comment_rate_of_change=round(metric_rates_of_change.get(MetricType.COMMENT, 0.0), 4),
            share_mean_5m=round(metric_means.get(MetricType.SHARE, 0.0), 4),
            share_z_score=round(metric_z_scores.get(MetricType.SHARE, 0.0), 4),
            share_rate_of_change=round(metric_rates_of_change.get(MetricType.SHARE, 0.0), 4),
            composite_s_score=round(composite_s_score, 4),
            micro_variance_ratio=round(micro_variance_ratio, 4),
            diurnal_sin=round(sin_t, 4),
            diurnal_cos=round(cos_t, 4),
        )

    @classmethod
    def generate_synthetic_dataset(
        cls, num_samples: int = 500, horizon_minutes: int = 15, seed: int = 42
    ) -> Tuple[np.ndarray, np.ndarray, List[MLFeatureVector]]:
        """
        Generates synthetic training dataset (X, y) with binary target labels (1 = degraded h mins ahead).
        """
        np_rng = np.random.default_rng(seed)
        t_start = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)

        feature_vectors: List[MLFeatureVector] = []
        labels: List[int] = []

        for i in range(num_samples):
            t_curr = t_start.replace(minute=(i * 2) % 60)
            
            # 20% of dataset simulates pre-policy degradation warning trajectory
            is_degrading_soon = (i % 5 == 0)

            if is_degrading_soon:
                l_z = float(np_rng.normal(2.5, 0.5))
                c_z = float(np_rng.normal(2.0, 0.5))
                s_z = float(np_rng.normal(2.2, 0.5))
                roc = float(np_rng.normal(-0.15, 0.05))
                comp_s = l_z**2 + c_z**2 + s_z**2
                target_y = 1
            else:
                l_z = float(np_rng.normal(0.0, 0.5))
                c_z = float(np_rng.normal(0.0, 0.5))
                s_z = float(np_rng.normal(0.0, 0.5))
                roc = float(np_rng.normal(0.0, 0.02))
                comp_s = max(0.0, l_z)**2 + max(0.0, c_z)**2 + max(0.0, s_z)**2
                target_y = 0

            vec = cls.build_feature_vector(
                timestamp=t_curr,
                metric_means={MetricType.LIKE: 100.0 - l_z, MetricType.COMMENT: 50.0 - c_z, MetricType.SHARE: 20.0 - s_z},
                metric_z_scores={MetricType.LIKE: l_z, MetricType.COMMENT: c_z, MetricType.SHARE: s_z},
                metric_rates_of_change={MetricType.LIKE: roc, MetricType.COMMENT: roc, MetricType.SHARE: roc},
                composite_s_score=comp_s,
            )
            feature_vectors.append(vec)
            labels.append(target_y)

        X = np.array([v.to_numpy() for v in feature_vectors], dtype=np.float64)
        y = np.array(labels, dtype=np.int32)
        return X, y, feature_vectors
