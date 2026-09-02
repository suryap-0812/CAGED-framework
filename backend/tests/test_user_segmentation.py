"""
Unit Tests for Privacy-Safe Streaming User Segmentation.
"""

from datetime import datetime, timezone
import numpy as np
import pytest

from app.ingestion.models import EngagementEvent, MetricType
from app.preprocessing.privacy import FORBIDDEN_FIELDS, pseudonymize_user_id
from app.segmentation.feature_extractor import UserFeatureExtractor, UserFeatureVector
from app.segmentation.streaming_clusterer import StreamingUserClusterer


def test_user_feature_extractor_without_private_fields():
    """Verifies that UserFeatureExtractor extracts valid behavioral features with 0 private fields."""
    u1_hash = pseudonymize_user_id("user_seg_1")
    u2_hash = pseudonymize_user_id("user_seg_2")

    events = [
        EngagementEvent(event_id="e1", user_hash=u1_hash, metric_type=MetricType.VIEW, timestamp=datetime.now(timezone.utc), content_category="technology"),
        EngagementEvent(event_id="e2", user_hash=u1_hash, metric_type=MetricType.LIKE, timestamp=datetime.now(timezone.utc), content_category="technology"),
        EngagementEvent(event_id="e3", user_hash=u1_hash, metric_type=MetricType.SESSION_DURATION, value=120.0, timestamp=datetime.now(timezone.utc), content_category="education"),
        EngagementEvent(event_id="e4", user_hash=u2_hash, metric_type=MetricType.COMMENT, timestamp=datetime.now(timezone.utc), content_category="news"),
    ]

    features = UserFeatureExtractor.extract_features(events)

    assert len(features) == 2
    assert u1_hash in features
    assert u2_hash in features

    vec1 = features[u1_hash]
    assert vec1.interaction_count == 3
    assert vec1.avg_session_duration == 120.0
    assert vec1.metric_ratios[MetricType.LIKE.value] == round(1.0 / 3.0, 4)

    # Check numpy array conversion
    np_arr = vec1.to_numpy()
    assert len(np_arr) == 13
    assert not np.isnan(np_arr).any()

    # Ensure no forbidden private fields in model dict
    dict_rep = vec1.model_dump()
    for forbidden in FORBIDDEN_FIELDS:
        assert forbidden not in dict_rep


def test_streaming_user_clusterer_partial_fit_and_summaries():
    """Tests incremental partial_fit and cluster summary generation using MiniBatchKMeans."""
    clusterer = StreamingUserClusterer(n_clusters=3, batch_size=20, random_state=42)

    # Generate synthetic feature vectors representing distinct behavioral clusters
    u_vectors = []
    
    # Cluster A: Heavy Likers (10 users)
    for i in range(10):
        u_hash = pseudonymize_user_id(f"user_a_{i}")
        u_vectors.append(
            UserFeatureVector(
                user_hash=u_hash,
                interaction_count=50,
                avg_session_duration=300.0,
                metric_ratios={"like": 0.80, "view": 0.20},
                category_ratios={"technology": 1.0},
            )
        )

    # Cluster B: Heavy Viewers (10 users)
    for i in range(10):
        u_hash = pseudonymize_user_id(f"user_b_{i}")
        u_vectors.append(
            UserFeatureVector(
                user_hash=u_hash,
                interaction_count=5,
                avg_session_duration=30.0,
                metric_ratios={"view": 0.90, "like": 0.10},
                category_ratios={"entertainment": 1.0},
            )
        )

    clusterer.partial_fit(u_vectors)

    assert clusterer.is_fitted is True

    # Predict cluster for new vector similar to Cluster A
    new_liker = UserFeatureVector(
        user_hash=pseudonymize_user_id("new_liker"),
        interaction_count=45,
        avg_session_duration=280.0,
        metric_ratios={"like": 0.85, "view": 0.15},
        category_ratios={"technology": 1.0},
    )
    predicted_cid = clusterer.predict_cluster(new_liker)
    assert 0 <= predicted_cid < 3

    # Check summaries
    summaries = clusterer.get_cluster_summaries()
    assert len(summaries) == 3
    
    for cid, summary in summaries.items():
        assert summary.cluster_id == cid
        assert summary.dominant_metric in [m.value for m in MetricType]
        assert summary.dominant_category in ["technology", "entertainment", "education", "news", "gaming", "lifestyle"]
