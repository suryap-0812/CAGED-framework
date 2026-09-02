"""
Segment-Level Degradation Detector & Localization Engine for CAGED.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.baselines.base import BaselinePrediction
from app.detection.multi_metric import MultiMetricDegradationResult, MultiMetricDetector
from app.detection.single_metric import MetricDegradationResult, StatisticalDegradationDetector
from app.ingestion.models import MetricType


class SegmentDegradationResult(BaseModel):
    """Result of multi-metric degradation evaluation for a specific user segment or cluster."""

    segment_id: str = Field(..., description="Segment or cluster identifier")
    policy_id: Optional[str] = Field(default=None, description="Associated policy identifier")
    timestamp: datetime = Field(..., description="UTC timestamp of evaluation")
    composite_score: float = Field(..., description="Segment composite score S_s = sum max(Z_{s,m}, 0)^2")
    composite_threshold: float = Field(default=4.0, description="Segment threshold")
    is_degraded: bool = Field(..., description="True if segment score S_s >= threshold")
    metric_results: Dict[str, MetricDegradationResult] = Field(..., description="Per-metric degradation for segment")
    top_degraded_metric: Optional[MetricType] = Field(default=None, description="Highest degraded metric in segment")


class SegmentComparisonReport(BaseModel):
    """Comparative localization report contrasting overall platform vs segment degradation."""

    policy_id: Optional[str] = Field(default=None, description="Associated policy identifier")
    timestamp: datetime = Field(..., description="UTC timestamp of evaluation")
    overall_composite_score: float = Field(..., description="Platform-wide overall composite score")
    overall_is_degraded: bool = Field(..., description="Platform-wide degradation boolean")
    segment_results: Dict[str, SegmentDegradationResult] = Field(..., description="Per-segment degradation results")
    ranked_segments: List[Tuple[str, float]] = Field(..., description="Segments ranked by composite score S_s")
    most_degraded_segment: Optional[str] = Field(default=None, description="Segment ID with highest degradation")
    least_degraded_segment: Optional[str] = Field(default=None, description="Segment ID with lowest degradation")
    is_localized: bool = Field(..., description="True if degradation is concentrated in specific segment(s)")


class SegmentDegradationDetector:
    """
    Detector evaluating segment-level metrics and localizing engagement degradation.
    """

    def __init__(
        self,
        multi_metric_detector: Optional[MultiMetricDetector] = None,
        default_segment_threshold: float = 4.0,
    ):
        self.multi_detector = multi_metric_detector or MultiMetricDetector()
        self.default_segment_threshold = default_segment_threshold

    def evaluate_segment(
        self,
        segment_id: str,
        observed_metrics: Dict[MetricType, float],
        baseline_predictions: Dict[MetricType, BaselinePrediction],
        policy_id: Optional[str] = None,
        threshold: Optional[float] = None,
        timestamp: Optional[datetime] = None,
    ) -> SegmentDegradationResult:
        """
        Evaluates composite degradation for a single user segment.
        """
        eval_time = timestamp or datetime.now(timezone.utc)
        if eval_time.tzinfo is None:
            eval_time = eval_time.replace(tzinfo=timezone.utc)

        s_thresh = threshold if threshold is not None else self.default_segment_threshold

        multi_res = self.multi_detector.evaluate(
            observed_metrics=observed_metrics,
            baseline_predictions=baseline_predictions,
            policy_id=policy_id,
            composite_threshold=s_thresh,
            timestamp=eval_time,
        )

        return SegmentDegradationResult(
            segment_id=segment_id,
            policy_id=policy_id,
            timestamp=eval_time,
            composite_score=multi_res.composite_score,
            composite_threshold=s_thresh,
            is_degraded=multi_res.is_degraded,
            metric_results=multi_res.metric_results,
            top_degraded_metric=multi_res.top_contributor,
        )

    def evaluate_all_segments(
        self,
        overall_observed: Dict[MetricType, float],
        overall_predictions: Dict[MetricType, BaselinePrediction],
        segment_observed: Dict[str, Dict[MetricType, float]],
        segment_predictions: Dict[str, Dict[MetricType, BaselinePrediction]],
        policy_id: Optional[str] = None,
        threshold: Optional[float] = None,
        timestamp: Optional[datetime] = None,
    ) -> SegmentComparisonReport:
        """
        Evaluates overall and per-segment degradation, ranking segments and localizing impact.
        """
        eval_time = timestamp or datetime.now(timezone.utc)
        if eval_time.tzinfo is None:
            eval_time = eval_time.replace(tzinfo=timezone.utc)

        s_thresh = threshold if threshold is not None else self.default_segment_threshold

        # 1. Evaluate Overall Platform Multi-Metric Degradation
        overall_res = self.multi_detector.evaluate(
            observed_metrics=overall_observed,
            baseline_predictions=overall_predictions,
            policy_id=policy_id,
            composite_threshold=s_thresh,
            timestamp=eval_time,
        )

        # 2. Evaluate Each Segment
        seg_results: Dict[str, SegmentDegradationResult] = {}
        for seg_id, obs_dict in segment_observed.items():
            pred_dict = segment_predictions.get(seg_id, {})
            seg_res = self.evaluate_segment(
                segment_id=seg_id,
                observed_metrics=obs_dict,
                baseline_predictions=pred_dict,
                policy_id=policy_id,
                threshold=s_thresh,
                timestamp=eval_time,
            )
            seg_results[seg_id] = seg_res

        # 3. Rank Segments by Composite Score S_s Descending
        ranked = [(seg_id, res.composite_score) for seg_id, res in seg_results.items()]
        ranked.sort(key=lambda pair: pair[1], reverse=True)

        most_degraded = ranked[0][0] if ranked and ranked[0][1] > 0 else None
        least_degraded = ranked[-1][0] if ranked else None

        # Check localization: is max segment score > 2x average segment score?
        scores = [score for _, score in ranked]
        avg_score = float(sum(scores) / len(scores)) if scores else 0.0
        max_score = scores[0] if scores else 0.0

        is_localized = (max_score > 2.0 * avg_score) if (avg_score > 0 and max_score >= s_thresh) else False

        return SegmentComparisonReport(
            policy_id=policy_id,
            timestamp=eval_time,
            overall_composite_score=overall_res.composite_score,
            overall_is_degraded=overall_res.is_degraded,
            segment_results=seg_results,
            ranked_segments=ranked,
            most_degraded_segment=most_degraded,
            least_degraded_segment=least_degraded,
            is_localized=is_localized,
        )
