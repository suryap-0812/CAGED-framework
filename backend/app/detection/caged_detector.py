"""
CAGED Core Statistical Detection Engine.
Operates strictly on observable telemetry, 5-minute window rate normalization,
frozen pre-policy baselines, composite Z-scores, calibrated thresholds, and segment localization.
Independently executable from ML predictions.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import numpy as np
from pydantic import BaseModel, Field

from app.ingestion.models import EngagementEvent, MetricType
from app.detection.window_aggregator import WindowAggregator, WindowedMetricPoint


class MetricWindowResult(BaseModel):
    """Evaluation result for a single metric in a 5-minute window."""

    metric_type: MetricType = Field(..., description="Target metric")
    observed_rate: float = Field(..., description="Observed rate in window Y_{m, t}")
    baseline_mean: float = Field(..., description="Frozen baseline mean mu_{m, frozen}")
    baseline_std: float = Field(..., description="Frozen baseline std dev sigma_{m, frozen}")
    z_score: float = Field(..., description="Standardized Z-score deviation Z_{m, t}")
    positive_z_score: float = Field(..., description="Positive Z-score max(Z, 0)")
    relative_change: float = Field(..., description="Relative change (Y - mu) / mu")


class WindowDetectionResult(BaseModel):
    """Detection decision container for a single 5-minute window."""

    window_start: datetime = Field(..., description="Window UTC start time")
    window_end: datetime = Field(..., description="Window UTC end time")
    window_index: int = Field(..., description="Sequential window index")
    is_post_t0: bool = Field(..., description="True if window start >= T0")
    
    composite_score: float = Field(..., description="Composite score S_t = sum max(Z_m, 0)^2")
    composite_threshold: float = Field(..., description="Detection threshold S_threshold")
    is_degraded: bool = Field(..., description="True if S_t >= threshold and max_drop >= Delta_min")
    
    metric_results: Dict[str, MetricWindowResult] = Field(..., description="Per-metric window results")
    top_degraded_metric: Optional[MetricType] = Field(default=None, description="Highest contributing metric")
    
    most_degraded_segment: Optional[str] = Field(default=None, description="Top degraded user segment")
    most_degraded_category: Optional[str] = Field(default=None, description="Top degraded content category")


class CAGEDDetectionReport(BaseModel):
    """Full session detection report produced by CAGED Statistical Detection Engine."""

    t0: Optional[datetime] = Field(default=None, description="Intervention onset timestamp T0")
    is_degradation_detected: bool = Field(..., description="True if any post-T0 window triggered alert")
    first_alert_timestamp: Optional[datetime] = Field(default=None, description="UTC timestamp of initial alert window T_alert")
    detection_latency_minutes: Optional[float] = Field(default=None, description="Latency in minutes from T0 to T_alert")
    
    peak_composite_score: float = Field(..., description="Maximum composite score S_t observed")
    calibrated_threshold: float = Field(..., description="Applied composite threshold S_threshold")
    minimum_effect_size: float = Field(..., description="Practical effect threshold Delta_min")
    
    frozen_baseline_means: Dict[str, float] = Field(..., description="Frozen baseline metric means")
    frozen_baseline_stds: Dict[str, float] = Field(..., description="Frozen baseline metric standard deviations")
    
    window_results: List[WindowDetectionResult] = Field(..., description="Sequential 5-minute window decisions")
    top_degraded_metric: Optional[MetricType] = Field(default=None, description="Overall top degraded metric")
    most_degraded_segment: Optional[str] = Field(default=None, description="Overall top degraded user segment")
    most_degraded_category: Optional[str] = Field(default=None, description="Overall top degraded content category")


class CAGEDStatisticalDetector:
    """
    Central Core Statistical Detection Engine for CAGED.
    Independent from ML predictions.
    """

    def __init__(
        self,
        composite_threshold: float = 4.0,
        minimum_effect_size: float = 0.05,
        window_size_minutes: int = 5,
        min_std_dev: float = 1e-4,
    ):
        self.composite_threshold = composite_threshold
        self.minimum_effect_size = minimum_effect_size
        self.aggregator = WindowAggregator(window_size_minutes=window_size_minutes)
        self.min_std_dev = min_std_dev

    def analyze_stream(
        self,
        events: List[EngagementEvent],
        t0: Optional[datetime] = None,
        composite_threshold: Optional[float] = None,
    ) -> CAGEDDetectionReport:
        """
        Executes 5-minute window rate aggregation, freezes baseline at T0,
        evaluates Z-scores and composite score S_t, measures detection latency,
        and localizes degraded segments and categories.
        """
        s_thresh = composite_threshold if composite_threshold is not None else self.composite_threshold
        if not events:
            return CAGEDDetectionReport(
                t0=t0,
                is_degradation_detected=False,
                peak_composite_score=0.0,
                calibrated_threshold=s_thresh,
                minimum_effect_size=self.minimum_effect_size,
                frozen_baseline_means={},
                frozen_baseline_stds={},
                window_results=[],
            )

        window_points = self.aggregator.aggregate_stream(events)
        start_time = window_points[0].window_start
        onset_t0 = t0 or (start_time + timedelta(hours=12.0))
        if onset_t0.tzinfo is None:
            onset_t0 = onset_t0.replace(tzinfo=timezone.utc)

        # 1. Separate Pre-T0 vs Post-T0 Windows
        pre_windows = [pt for pt in window_points if pt.window_start < onset_t0]
        post_windows = [pt for pt in window_points if pt.window_start >= onset_t0]

        if not pre_windows:
            pre_windows = window_points[: len(window_points) // 2]
            post_windows = window_points[len(window_points) // 2 :]

        metrics = [
            MetricType.VIEW,
            MetricType.LIKE,
            MetricType.COMMENT,
            MetricType.SHARE,
            MetricType.CLICK,
            MetricType.SESSION_DURATION,
        ]

        # 2. Compute and Freeze Pre-Policy Baseline Parameters
        frozen_means: Dict[MetricType, float] = {}
        frozen_stds: Dict[MetricType, float] = {}

        for m in metrics:
            vals = [pt.get_metric_value(m) for pt in pre_windows]
            mu = float(np.mean(vals)) if vals else 0.0
            sd = float(np.std(vals, ddof=1)) if len(vals) > 1 else self.min_std_dev
            frozen_means[m] = mu
            frozen_stds[m] = max(sd, self.min_std_dev)

        # 3. Evaluate Sequential Window Decisions
        window_results: List[WindowDetectionResult] = []
        is_detected = False
        first_alert_time: Optional[datetime] = None
        peak_score = 0.0

        for pt in window_points:
            is_post = pt.window_start >= onset_t0
            m_res: Dict[str, MetricWindowResult] = {}
            total_s = 0.0
            max_relative_drop = 0.0
            metric_s_scores: List[Tuple[MetricType, float]] = []

            for m in metrics:
                obs = pt.get_metric_value(m)
                mu = frozen_means[m]
                sd = frozen_stds[m]

                # Z-score deviation (positive means metric fell below expected baseline)
                z_t = (mu - obs) / sd
                z_pos = max(z_t, 0.0)
                sq_z = z_pos ** 2
                total_s += sq_z

                rel_change = ((obs - mu) / mu) if mu > 0 else 0.0
                rel_drop = ((mu - obs) / mu) if mu > 0 else 0.0
                if rel_drop > max_relative_drop:
                    max_relative_drop = rel_drop

                m_res[m.value] = MetricWindowResult(
                    metric_type=m,
                    observed_rate=round(obs, 4),
                    baseline_mean=round(mu, 4),
                    baseline_std=round(sd, 6),
                    z_score=round(z_t, 4),
                    positive_z_score=round(z_pos, 4),
                    relative_change=round(rel_change, 4),
                )
                metric_s_scores.append((m, sq_z))

            metric_s_scores.sort(key=lambda pair: pair[1], reverse=True)
            top_metric_win = metric_s_scores[0][0] if (metric_s_scores and metric_s_scores[0][1] > 0) else None

            # Segment breakdown for window
            top_seg = None
            if pt.segment_breakdown:
                seg_counts = {seg: sum(counts.values()) for seg, counts in pt.segment_breakdown.items()}
                top_seg = max(seg_counts.items(), key=lambda p: p[1])[0] if seg_counts else None

            top_cat = None
            if pt.category_breakdown:
                cat_counts = {cat: sum(counts.values()) for cat, counts in pt.category_breakdown.items()}
                top_cat = max(cat_counts.items(), key=lambda p: p[1])[0] if cat_counts else None

            # Window alert trigger condition
            win_degraded = is_post and (total_s >= s_thresh) and (max_relative_drop >= self.minimum_effect_size)

            if win_degraded and not is_detected:
                is_detected = True
                first_alert_time = pt.window_start

            if total_s > peak_score:
                peak_score = total_s

            window_results.append(
                WindowDetectionResult(
                    window_start=pt.window_start,
                    window_end=pt.window_end,
                    window_index=pt.window_index,
                    is_post_t0=is_post,
                    composite_score=round(total_s, 4),
                    composite_threshold=s_thresh,
                    is_degraded=win_degraded,
                    metric_results=m_res,
                    top_degraded_metric=top_metric_win,
                    most_degraded_segment=top_seg,
                    most_degraded_category=top_cat,
                )
            )

        # 4. Latency Calculation
        latency_min: Optional[float] = None
        if first_alert_time and onset_t0:
            latency_sec = (first_alert_time - onset_t0).total_seconds()
            latency_min = round(max(0.0, latency_sec / 60.0), 2)

        # Overall top degraded metric & localization
        post_window_results = [w for w in window_results if w.is_post_t0 and w.is_degraded]
        overall_top_metric = post_window_results[0].top_degraded_metric if post_window_results else None
        overall_top_seg = post_window_results[0].most_degraded_segment if post_window_results else None
        overall_top_cat = post_window_results[0].most_degraded_category if post_window_results else None

        return CAGEDDetectionReport(
            t0=onset_t0,
            is_degradation_detected=is_detected,
            first_alert_timestamp=first_alert_time,
            detection_latency_minutes=latency_min,
            peak_composite_score=round(peak_score, 4),
            calibrated_threshold=s_thresh,
            minimum_effect_size=self.minimum_effect_size,
            frozen_baseline_means={m.value: round(v, 4) for m, v in frozen_means.items()},
            frozen_baseline_stds={m.value: round(v, 6) for m, v in frozen_stds.items()},
            window_results=window_results,
            top_degraded_metric=overall_top_metric,
            most_degraded_segment=overall_top_seg,
            most_degraded_category=overall_top_cat,
        )
