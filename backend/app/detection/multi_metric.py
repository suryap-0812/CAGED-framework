"""
Multi-Metric Composite Degradation Score Detector for CAGED.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.baselines.base import BaselinePrediction
from app.detection.single_metric import MetricDegradationResult, StatisticalDegradationDetector
from app.ingestion.models import MetricType


class MetricContribution(BaseModel):
    """Details metric contribution to composite degradation score S."""

    metric_type: MetricType = Field(..., description="Metric identifier")
    z_score: float = Field(..., description="Raw Z-score deviation Z_k")
    positive_z_score: float = Field(..., description="Positive Z-score max(Z_k, 0)")
    squared_z_score: float = Field(..., description="Squared positive Z-score max(Z_k, 0)^2")
    contribution_ratio: float = Field(..., description="Proportion of total composite score (0.0 to 1.0)")
    contribution_percentage: float = Field(..., description="Percentage contribution to score S")


class MultiMetricDegradationResult(BaseModel):
    """Result container for multi-metric composite degradation scoring."""

    policy_id: Optional[str] = Field(default=None, description="Associated policy identifier")
    timestamp: datetime = Field(..., description="UTC timestamp of evaluation")
    composite_score: float = Field(..., description="Composite degradation score S = sum max(Z_k, 0)^2")
    composite_threshold: float = Field(default=4.0, description="Configured composite degradation threshold S_thresh")
    is_degraded: bool = Field(..., description="True if composite_score >= composite_threshold")
    metric_results: Dict[str, MetricDegradationResult] = Field(..., description="Per-metric degradation details")
    contributing_metrics: List[MetricContribution] = Field(..., description="Metrics ranked by contribution")
    top_contributor: Optional[MetricType] = Field(default=None, description="Highest contributing metric")


class MultiMetricDetector:
    """
    Multi-Metric Composite Degradation Detector.
    
    Formula:
        S = sum_k max(Z_k, 0)^2
    """

    def __init__(
        self,
        single_metric_detector: Optional[StatisticalDegradationDetector] = None,
        default_composite_threshold: float = 4.0,
    ):
        """
        Args:
            single_metric_detector: Single metric detector instance.
            default_composite_threshold: Composite score threshold (default: 4.0).
        """
        self.single_detector = single_metric_detector or StatisticalDegradationDetector()
        self.default_composite_threshold = default_composite_threshold

    def evaluate(
        self,
        observed_metrics: Dict[MetricType, float],
        baseline_predictions: Dict[MetricType, BaselinePrediction],
        policy_id: Optional[str] = None,
        composite_threshold: Optional[float] = None,
        single_threshold: Optional[float] = None,
        timestamp: Optional[datetime] = None,
    ) -> MultiMetricDegradationResult:
        """
        Evaluates composite multi-metric degradation across all metrics.
        
        Args:
            observed_metrics: Dict mapping MetricType -> observed value O_k.
            baseline_predictions: Dict mapping MetricType -> frozen baseline forecast E_k.
            policy_id: Associated policy ID.
            composite_threshold: Custom threshold for composite score S.
            single_threshold: Custom threshold for per-metric Z-score test.
            timestamp: Evaluation UTC timestamp.
            
        Returns:
            MultiMetricDegradationResult instance.
        """
        eval_time = timestamp or datetime.now(timezone.utc)
        if eval_time.tzinfo is None:
            eval_time = eval_time.replace(tzinfo=timezone.utc)

        s_thresh = composite_threshold if composite_threshold is not None else self.default_composite_threshold

        per_metric_results: Dict[str, MetricDegradationResult] = {}
        contributions: List[MetricContribution] = []

        total_composite_score = 0.0

        # Evaluate each metric present in observations or predictions
        all_metrics = set(observed_metrics.keys()).union(set(baseline_predictions.keys()))
        
        for m in all_metrics:
            obs = observed_metrics.get(m)
            pred = baseline_predictions.get(m)

            res = self.single_detector.evaluate(
                metric_type=m,
                observed_value=obs,
                baseline_prediction=pred,
                policy_id=policy_id,
                threshold=single_threshold,
                timestamp=eval_time,
            )

            per_metric_results[m.value] = res

            z_pos = res.positive_z_score
            sq_z = z_pos ** 2
            total_composite_score += sq_z

        # Compute relative contribution proportions
        for m_str, res in per_metric_results.items():
            metric_enum = MetricType(m_str)
            z_pos = res.positive_z_score
            sq_z = z_pos ** 2
            
            ratio = (sq_z / total_composite_score) if total_composite_score > 0 else 0.0
            
            contributions.append(
                MetricContribution(
                    metric_type=metric_enum,
                    z_score=res.z_score,
                    positive_z_score=z_pos,
                    squared_z_score=round(sq_z, 4),
                    contribution_ratio=round(ratio, 4),
                    contribution_percentage=round(ratio * 100.0, 2),
                )
            )

        # Sort contributions in descending order of squared Z-score
        contributions.sort(key=lambda c: c.squared_z_score, reverse=True)

        top_metric = contributions[0].metric_type if (contributions and contributions[0].squared_z_score > 0) else None
        is_degraded = total_composite_score >= s_thresh

        return MultiMetricDegradationResult(
            policy_id=policy_id,
            timestamp=eval_time,
            composite_score=round(total_composite_score, 4),
            composite_threshold=s_thresh,
            is_degraded=is_degraded,
            metric_results=per_metric_results,
            contributing_metrics=contributions,
            top_contributor=top_metric,
        )
