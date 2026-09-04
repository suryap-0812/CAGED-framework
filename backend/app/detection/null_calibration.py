"""
Null Distribution Calibration Engine for CAGED Detector.
Simulates K null iterations (H0: NO_POLICY) under independent seeds to target false-alarm rate alpha <= 0.05.
"""

from datetime import datetime, timezone
from typing import Dict, List, Tuple
import numpy as np
from pydantic import BaseModel, Field

from app.ingestion.models import MetricType
from app.simulation.event_generator import EventGenerator
from app.simulation.experiment_config import ExperimentConfig, PolicyMechanism
from app.detection.window_aggregator import WindowAggregator, WindowedMetricPoint


class NullCalibrationReport(BaseModel):
    """Container for null distribution calibration outputs."""

    k_iterations: int = Field(..., description="Total null simulation iterations K")
    target_alpha: float = Field(..., description="Target false-alarm rate alpha (e.g. 0.05)")
    calibrated_s_threshold: float = Field(..., description="Empirical (1-alpha) quantile threshold S_threshold")
    empirical_false_alarm_rate: float = Field(..., description="Empirical false alarm rate on null distribution")
    null_scores_distribution: List[float] = Field(..., description="Sample of maximum null composite scores")
    is_calibrated: bool = Field(..., description="True if calibration completed successfully")


class NullThresholdCalibrator:
    """
    Calibrates detection threshold S_threshold using independent null simulations (H0: NO_POLICY).
    """

    def __init__(
        self,
        k_iterations: int = 100,
        target_alpha: float = 0.05,
        base_seed: int = 50000,
    ):
        self.k_iterations = max(10, k_iterations)
        self.target_alpha = target_alpha
        self.base_seed = base_seed
        self.aggregator = WindowAggregator(window_size_minutes=5)

    def run_null_calibration(self) -> NullCalibrationReport:
        """
        Executes K null simulations under NO_POLICY with independent random seeds
        to estimate empirical quantile Q_(1-alpha)(S_null).
        """
        null_max_scores: List[float] = []

        # Fast K independent null iterations using lightweight num_events=100
        for k in range(self.k_iterations):
            seed = self.base_seed + k
            config = ExperimentConfig(
                seed=seed,
                num_users=50,
                num_items=30,
                num_events=100,
                duration_hours=2.0,
                policy_mechanism=PolicyMechanism.NO_POLICY,
            )
            generator = EventGenerator(config)
            events = generator.generate_events()

            # Split into baseline (first half) and test (second half)
            mid_idx = len(events) // 2
            pre_evts = events[:mid_idx]
            post_evts = events[mid_idx:]

            pre_pts = self.aggregator.aggregate_stream(pre_evts)
            post_pts = self.aggregator.aggregate_stream(post_evts)

            if not pre_pts or not post_pts:
                continue

            metrics = [MetricType.VIEW, MetricType.LIKE, MetricType.COMMENT, MetricType.SHARE, MetricType.CLICK, MetricType.SESSION_DURATION]
            base_means: Dict[MetricType, float] = {}
            base_stds: Dict[MetricType, float] = {}

            for m in metrics:
                vals = [pt.get_metric_value(m) for pt in pre_pts]
                mu = float(np.mean(vals)) if vals else 0.0
                sd = float(np.std(vals, ddof=1)) if len(vals) > 1 else 1e-4
                base_means[m] = mu
                base_stds[m] = max(sd, 1e-4)

            max_s = 0.0
            for pt in post_pts:
                s_t = 0.0
                for m in metrics:
                    obs = pt.get_metric_value(m)
                    z_t = (base_means[m] - obs) / base_stds[m]
                    z_pos = max(z_t, 0.0)
                    s_t += z_pos ** 2
                if s_t > max_s:
                    max_s = s_t

            null_max_scores.append(max_s)

        if not null_max_scores:
            return NullCalibrationReport(
                k_iterations=self.k_iterations,
                target_alpha=self.target_alpha,
                calibrated_s_threshold=4.0,
                empirical_false_alarm_rate=self.target_alpha,
                null_scores_distribution=[],
                is_calibrated=False,
            )

        null_arr = np.array(null_max_scores, dtype=np.float64)
        pct_val = 100.0 * (1.0 - self.target_alpha)
        calibrated_thresh = float(np.percentile(null_arr, pct_val))

        false_alarms = np.sum(null_arr >= calibrated_thresh)
        emp_far = float(false_alarms / len(null_arr))

        return NullCalibrationReport(
            k_iterations=len(null_max_scores),
            target_alpha=self.target_alpha,
            calibrated_s_threshold=round(calibrated_thresh, 4),
            empirical_false_alarm_rate=round(emp_far, 4),
            null_scores_distribution=[round(x, 4) for x in null_max_scores[:50]],
            is_calibrated=True,
        )
