"""
Single-Metric Statistical Degradation Detector for CAGED.
"""

from datetime import datetime, timezone
import math
from typing import Optional
from pydantic import BaseModel, Field
import scipy.stats as stats

from app.baselines.base import BaselineModel, BaselinePrediction
from app.ingestion.models import MetricType


class MetricDegradationResult(BaseModel):
    """Result of statistical degradation detection test for a single metric."""

    metric_type: MetricType = Field(..., description="Target metric type")
    policy_id: Optional[str] = Field(default=None, description="Associated policy identifier")
    timestamp: datetime = Field(..., description="UTC timestamp of evaluation")
    expected_value: float = Field(..., description="Expected baseline value E_t")
    observed_value: float = Field(..., description="Observed post-policy value O_t")
    deviation: float = Field(..., description="Raw degradation deviation D_t = E_t - O_t")
    baseline_std_dev: float = Field(..., description="Baseline residual standard deviation sigma_eta")
    z_score: float = Field(..., description="Standardized Z-score deviation Z = (E_t - O_t) / sigma_eta")
    positive_z_score: float = Field(..., description="Positive Z-score max(Z, 0)")
    threshold: float = Field(default=2.0, description="Configured degradation detection Z-threshold")
    is_degraded: bool = Field(..., description="True if positive Z-score exceeds threshold")
    p_value: float = Field(..., description="One-tailed p-value for degradation")
    status: str = Field(..., description="Status description ('degraded', 'stable', 'zero_variance', 'insufficient_data')")


class StatisticalDegradationDetector:
    """
    Core statistical detector evaluating single-metric engagement degradation.
    
    Formula:
        D_t = E_t - O_t
        Z_t = D_t / max(sigma_eta, min_std_dev)
        Z_deg = max(Z_t, 0.0)
    """

    def __init__(self, default_threshold: float = 2.0, min_std_dev: float = 1e-4):
        """
        Args:
            default_threshold: Z-score threshold for signaling degradation (default: 2.0 -> p < 0.0228).
            min_std_dev: Minimum standard deviation floor to prevent division by zero.
        """
        self.default_threshold = default_threshold
        self.min_std_dev = min_std_dev

    def evaluate(
        self,
        metric_type: MetricType,
        observed_value: Optional[float],
        baseline_prediction: Optional[BaselinePrediction],
        policy_id: Optional[str] = None,
        threshold: Optional[float] = None,
        timestamp: Optional[datetime] = None,
    ) -> MetricDegradationResult:
        """
        Evaluates post-policy observed value against frozen baseline expected value.
        
        Args:
            metric_type: Target metric.
            observed_value: Post-policy observed metric value O_t.
            baseline_prediction: Forecast from frozen pre-policy baseline E_t.
            policy_id: Associated policy ID.
            threshold: Custom Z-score threshold (overrides default_threshold).
            timestamp: Evaluation UTC timestamp.
            
        Returns:
            MetricDegradationResult instance.
        """
        eval_time = timestamp or datetime.now(timezone.utc)
        if eval_time.tzinfo is None:
            eval_time = eval_time.replace(tzinfo=timezone.utc)

        z_thresh = threshold if threshold is not None else self.default_threshold

        # Handle missing data or uninitialized baseline
        if observed_value is None or baseline_prediction is None:
            return MetricDegradationResult(
                metric_type=metric_type,
                policy_id=policy_id,
                timestamp=eval_time,
                expected_value=0.0,
                observed_value=0.0 if observed_value is None else float(observed_value),
                deviation=0.0,
                baseline_std_dev=0.0,
                z_score=0.0,
                positive_z_score=0.0,
                threshold=z_thresh,
                is_degraded=False,
                p_value=1.0,
                status="insufficient_data",
            )

        E_t = baseline_prediction.expected_value
        O_t = float(observed_value)
        D_t = E_t - O_t  # Positive D_t means observed fell below expected

        raw_sigma = baseline_prediction.std_dev
        is_zero_variance = raw_sigma < self.min_std_dev
        sigma = max(raw_sigma, self.min_std_dev)

        # Standardized Z-score
        Z_t = D_t / sigma
        Z_deg = max(Z_t, 0.0)  # Only positive degradation contributes

        # One-tailed p-value calculation: P(Z >= Z_deg) under N(0, 1)
        p_val = float(1.0 - stats.norm.cdf(Z_deg))

        is_degraded = Z_deg >= z_thresh

        if is_zero_variance and abs(D_t) > 1e-4:
            status = "degraded" if is_degraded else "zero_variance"
        elif is_degraded:
            status = "degraded"
        else:
            status = "stable"

        return MetricDegradationResult(
            metric_type=metric_type,
            policy_id=policy_id,
            timestamp=eval_time,
            expected_value=round(E_t, 4),
            observed_value=round(O_t, 4),
            deviation=round(D_t, 4),
            baseline_std_dev=round(sigma, 6),
            z_score=round(Z_t, 4),
            positive_z_score=round(Z_deg, 4),
            threshold=z_thresh,
            is_degraded=is_degraded,
            p_value=round(p_val, 6),
            status=status,
        )
