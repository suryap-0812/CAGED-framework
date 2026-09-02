"""
Streaming Online User Clustering Engine using MiniBatchKMeans for CAGED.
"""

from typing import Dict, List, Optional
import numpy as np
from pydantic import BaseModel, Field
from sklearn.cluster import MiniBatchKMeans

from app.segmentation.feature_extractor import (
    FEATURE_CATEGORIES,
    FEATURE_METRICS,
    UserFeatureVector,
)

FEATURE_NAMES: List[str] = [
    "log_interaction_count",
    "log_avg_session_duration",
] + [f"ratio_{m.value}" for m in FEATURE_METRICS] + [f"cat_{cat}" for cat in FEATURE_CATEGORIES]


class ClusterSummary(BaseModel):
    """Summary representation of an identified user behavioral cluster."""

    cluster_id: int = Field(..., description="Unique cluster identifier integer")
    cluster_size: int = Field(default=0, description="Total assigned users in cluster")
    center_features: Dict[str, float] = Field(..., description="Centroid feature values")
    dominant_metric: str = Field(..., description="Dominant metric in cluster centroid")
    dominant_category: str = Field(..., description="Dominant category in cluster centroid")


class StreamingUserClusterer:
    """
    Incremental online clustering of user behavioral feature vectors using MiniBatchKMeans.
    """

    def __init__(self, n_clusters: int = 4, batch_size: int = 100, random_state: int = 42):
        self.n_clusters = n_clusters
        self.batch_size = batch_size
        self.random_state = random_state
        
        self.kmeans = MiniBatchKMeans(
            n_clusters=n_clusters,
            batch_size=batch_size,
            random_state=random_state,
            n_init=3,
        )
        self.is_fitted: bool = False
        self.cluster_counts: Dict[int, int] = {i: 0 for i in range(n_clusters)}
        self.user_cluster_map: Dict[str, int] = {}

    def partial_fit(self, user_vectors: List[UserFeatureVector]) -> None:
        """
        Incrementally updates online cluster centers with a new batch of user feature vectors.
        """
        if not user_vectors:
            return

        X = np.array([u.to_numpy() for u in user_vectors], dtype=np.float64)

        if not self.is_fitted:
            # Need at least n_clusters samples to initialize MiniBatchKMeans
            if len(user_vectors) < self.n_clusters:
                # Tile samples if batch is smaller than n_clusters
                tiles = (self.n_clusters // len(user_vectors)) + 1
                X_init = np.tile(X, (tiles, 1))[: self.n_clusters]
                self.kmeans.partial_fit(X_init)
            else:
                self.kmeans.partial_fit(X)
            self.is_fitted = True
        else:
            self.kmeans.partial_fit(X)

        # Update cluster counts and assignments
        labels = self.kmeans.predict(X)
        for u_vec, cluster_id in zip(user_vectors, labels):
            cid = int(cluster_id)
            self.user_cluster_map[u_vec.user_hash] = cid
            self.cluster_counts[cid] = self.cluster_counts.get(cid, 0) + 1

    def predict_cluster(self, user_vector: UserFeatureVector) -> int:
        """
        Predicts cluster assignment for a single user feature vector.
        """
        if not self.is_fitted:
            return 0

        X = np.array([user_vector.to_numpy()], dtype=np.float64)
        label = int(self.kmeans.predict(X)[0])
        return label

    def get_cluster_summaries(self) -> Dict[int, ClusterSummary]:
        """
        Calculates cluster summaries describing centroid features and dominant characteristics.
        """
        if not self.is_fitted:
            return {}

        centers = self.kmeans.cluster_centers_
        summaries: Dict[int, ClusterSummary] = {}

        for cid in range(self.n_clusters):
            center = centers[cid]
            feat_dict = {
                name: round(float(val), 4) for name, val in zip(FEATURE_NAMES, center)
            }

            # Find dominant metric ratio (indices 2 to 6)
            metric_ratios = {
                m.value: float(center[2 + idx]) for idx, m in enumerate(FEATURE_METRICS)
            }
            dom_metric = max(metric_ratios.items(), key=lambda pair: pair[1])[0]

            # Find dominant category ratio (indices 7 to 12)
            cat_ratios = {
                cat: float(center[7 + idx]) for idx, cat in enumerate(FEATURE_CATEGORIES)
            }
            dom_category = max(cat_ratios.items(), key=lambda pair: pair[1])[0]

            summaries[cid] = ClusterSummary(
                cluster_id=cid,
                cluster_size=self.cluster_counts.get(cid, 0),
                center_features=feat_dict,
                dominant_metric=dom_metric,
                dominant_category=dom_category,
            )

        return summaries

    def reset(self) -> None:
        """Resets clusterer state."""
        self.kmeans = MiniBatchKMeans(
            n_clusters=self.n_clusters,
            batch_size=self.batch_size,
            random_state=self.random_state,
            n_init=3,
        )
        self.is_fitted = False
        self.cluster_counts = {i: 0 for i in range(self.n_clusters)}
        self.user_cluster_map.clear()
