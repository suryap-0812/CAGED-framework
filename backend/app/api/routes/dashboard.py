"""
Dashboard API Routes providing real-time metric streams, policy timelines, alerts, and reports.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.baselines.base import BaselinePrediction
from app.baselines.exponential_smoothing import ExponentialSmoothingBaseline
from app.detection.multi_metric import MultiMetricDetector
from app.detection.segment_metric import SegmentDegradationDetector
from app.ingestion.models import MetricType
from app.ml.dataset import MLFeatureDatasetBuilder
from app.ml.predictor import XGBoostDegradationPredictor
from app.policy.freezer import BaselineSnapshotter
from app.policy.models import PolicyEvent
from app.policy.registry import PolicyTimeline
from app.reporting.alerts import AlertEngine
from app.reporting.reports import ReportEngine

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])

# Global state singleton for Dashboard endpoints
class DashboardState:
    def __init__(self):
        self.timeline = PolicyTimeline()
        self.snapshotter = BaselineSnapshotter()
        self.multi_detector = MultiMetricDetector(default_composite_threshold=4.0)
        self.segment_detector = SegmentDegradationDetector(default_segment_threshold=4.0)
        self.alert_engine = AlertEngine(suppression_window_seconds=60)
        self.ml_predictor = XGBoostDegradationPredictor(prediction_horizon_minutes=15)
        
        # Train ML predictor on startup
        X, y, _ = MLFeatureDatasetBuilder.generate_synthetic_dataset(num_samples=200, seed=42)
        self.ml_predictor.train(X, y)
        
        # Initial policy P001 at T0 = 2 hours ago
        self.t0 = datetime.now(timezone.utc) - timedelta(hours=2)
        self.policy_p001 = PolicyEvent(
            policy_id="P001",
            policy_name="Strict Recommendation Filter",
            timestamp=self.t0,
            description="Adjusted algorithmic feed sorting policy; stochastically suppresses low-relevance items.",
            impact_factor=0.75,  # -25% engagement drop post T0
        )
        self.timeline.add_policy_event(self.policy_p001)

        # Baseline predictions (pre-policy expected values)
        self.baselines = {
            MetricType.LIKE: BaselinePrediction(expected_value=100.0, variance=1.0, std_dev=1.0, ci_lower=98.0, ci_upper=102.0),
            MetricType.COMMENT: BaselinePrediction(expected_value=50.0, variance=1.0, std_dev=1.0, ci_lower=48.0, ci_upper=52.0),
            MetricType.SHARE: BaselinePrediction(expected_value=20.0, variance=0.5, std_dev=0.7071, ci_lower=18.6, ci_upper=21.4),
            MetricType.CLICK: BaselinePrediction(expected_value=150.0, variance=2.25, std_dev=1.5, ci_lower=147.0, ci_upper=153.0),
            MetricType.VIEW: BaselinePrediction(expected_value=500.0, variance=25.0, std_dev=5.0, ci_lower=490.0, ci_upper=510.0),
        }
        self.active_policy_id: Optional[str] = "P001"

state = DashboardState()


class PolicyTriggerRequest(BaseModel):
    policy_id: str = Field(default="P002")
    policy_name: str = Field(default="Ad-Load Adjustment")
    impact_factor: float = Field(default=0.70, description="Impact multiplier (0.70 = 30% drop)")
    description: str = Field(default="Increased ad frequency in feed")


@router.get("/metrics")
def get_dashboard_metrics():
    """
    Returns real-time time-series metric data comparing observed vs pre-policy counterfactual baselines,
    policy markers, Z-scores, and composite degradation score S.
    """
    now = datetime.now(timezone.utc)
    t0 = state.t0

    # Build 30 time steps (15 pre-policy, 15 post-policy)
    time_series = []
    for i in range(-15, 15):
        t_step = t0 + timedelta(minutes=i * 5)
        is_post = t_step >= t0

        drop_factor = state.policy_p001.impact_factor if (is_post and state.active_policy_id) else 1.0

        like_obs = 100.0 * drop_factor + (i % 3 - 1.0)
        comment_obs = 50.0 * drop_factor + (i % 2 - 0.5)
        share_obs = 20.0 * drop_factor + (i % 4 - 1.5)

        time_series.append({
            "timestamp": t_step.isoformat(),
            "is_post_policy": is_post,
            "like_expected": 100.0,
            "like_observed": round(like_obs, 2),
            "comment_expected": 50.0,
            "comment_observed": round(comment_obs, 2),
            "share_expected": 20.0,
            "share_observed": round(share_obs, 2),
        })

    # Evaluate current Multi-Metric Degradation
    curr_obs = {
        MetricType.LIKE: time_series[-1]["like_observed"],
        MetricType.COMMENT: time_series[-1]["comment_observed"],
        MetricType.SHARE: time_series[-1]["share_observed"],
    }
    curr_preds = {
        MetricType.LIKE: state.baselines[MetricType.LIKE],
        MetricType.COMMENT: state.baselines[MetricType.COMMENT],
        MetricType.SHARE: state.baselines[MetricType.SHARE],
    }

    multi_res = state.multi_detector.evaluate(
        observed_metrics=curr_obs,
        baseline_predictions=curr_preds,
        policy_id=state.active_policy_id,
        timestamp=now,
    )

    # Trigger alert evaluation
    state.alert_engine.evaluate_and_alert(multi_metric_result=multi_res, policy_id=state.active_policy_id, timestamp=now)

    return {
        "timestamp": now.isoformat(),
        "policy_t0": t0.isoformat(),
        "active_policy_id": state.active_policy_id,
        "composite_score": multi_res.composite_score,
        "composite_threshold": multi_res.composite_threshold,
        "is_degraded": multi_res.is_degraded,
        "top_contributor": multi_res.top_contributor.value if multi_res.top_contributor else None,
        "metric_results": multi_res.metric_results,
        "time_series": time_series,
    }


@router.get("/policies")
def get_dashboard_policies():
    """Returns policy timeline and registered policy events."""
    events = state.timeline.get_all_policy_events()
    return {
        "active_policy_id": state.active_policy_id,
        "policy_count": len(events),
        "policies": [e.model_dump() for e in events],
    }


@router.get("/segments")
def get_dashboard_segments():
    """Returns segment-level degradation scores and cluster summaries."""
    now = datetime.now(timezone.utc)
    base_pred = state.baselines[MetricType.LIKE]

    drop_factor = state.policy_p001.impact_factor if state.active_policy_id else 1.0

    seg_obs = {
        "casual": {MetricType.LIKE: 100.0},
        "regular": {MetricType.LIKE: 100.0 * drop_factor},
        "heavy": {MetricType.LIKE: 100.0 * drop_factor * 0.90},  # Heavy segment degraded most
        "content_focused": {MetricType.LIKE: 100.0},
    }

    seg_preds = {s: {MetricType.LIKE: base_pred} for s in seg_obs.keys()}

    report = state.segment_detector.evaluate_all_segments(
        overall_observed={MetricType.LIKE: 100.0 * drop_factor},
        overall_predictions={MetricType.LIKE: base_pred},
        segment_observed=seg_obs,
        segment_predictions=seg_preds,
        policy_id=state.active_policy_id,
        timestamp=now,
    )

    return report.model_dump()


@router.get("/alerts")
def get_dashboard_alerts():
    """Returns dispatched degradation alerts."""
    alerts = state.alert_engine.get_dispatched_alerts()
    return {
        "alert_count": len(alerts),
        "alerts": [a.model_dump() for a in reversed(alerts)],
    }


@router.get("/report")
def get_dashboard_report(format: str = Query(default="json", enum=["json", "markdown"])):
    """Returns formatted JSON or Markdown degradation report."""
    now = datetime.now(timezone.utc)
    curr_obs = {MetricType.LIKE: 75.0, MetricType.COMMENT: 37.5, MetricType.SHARE: 15.0}
    curr_preds = {
        MetricType.LIKE: state.baselines[MetricType.LIKE],
        MetricType.COMMENT: state.baselines[MetricType.COMMENT],
        MetricType.SHARE: state.baselines[MetricType.SHARE],
    }

    multi_res = state.multi_detector.evaluate(observed_metrics=curr_obs, baseline_predictions=curr_preds, policy_id=state.active_policy_id, timestamp=now)
    
    seg_report = state.segment_detector.evaluate_all_segments(
        overall_observed=curr_obs,
        overall_predictions=curr_preds,
        segment_observed={"heavy": curr_obs, "casual": {MetricType.LIKE: 100.0}},
        segment_predictions={"heavy": curr_preds, "casual": curr_preds},
        policy_id=state.active_policy_id,
    )

    # ML prediction early warning
    ml_vec = MLFeatureDatasetBuilder.build_feature_vector(
        timestamp=now,
        metric_means={MetricType.LIKE: 75.0, MetricType.COMMENT: 37.5, MetricType.SHARE: 15.0},
        metric_z_scores={MetricType.LIKE: 3.0, MetricType.COMMENT: 2.5, MetricType.SHARE: 2.8},
        metric_rates_of_change={MetricType.LIKE: -0.15, MetricType.COMMENT: -0.10, MetricType.SHARE: -0.12},
        composite_s_score=multi_res.composite_score,
    )
    ml_res = state.ml_predictor.predict_degradation_probability(ml_vec)

    report = ReportEngine.generate_report(
        policy_event=state.policy_p001,
        multi_metric_result=multi_res,
        segment_report=seg_report,
        ml_result=ml_res,
        generated_at=now,
    )

    if format == "markdown":
        return {"format": "markdown", "content": ReportEngine.export_markdown(report)}
    return {"format": "json", "report": report.model_dump()}


@router.post("/simulate_policy")
def simulate_policy_event(req: PolicyTriggerRequest):
    """Simulates a new policy trigger event at current timestamp T0."""
    now = datetime.now(timezone.utc)
    new_policy = PolicyEvent(
        policy_id=req.policy_id,
        policy_name=req.policy_name,
        timestamp=now,
        description=req.description,
        impact_factor=req.impact_factor,
    )

    state.timeline.add_policy_event(new_policy)
    state.policy_p001 = new_policy
    state.t0 = now
    state.active_policy_id = req.policy_id

    return {
        "status": "success",
        "message": f"Simulated policy event '{req.policy_id}' at {now.isoformat()}",
        "policy": new_policy.model_dump(),
    }
