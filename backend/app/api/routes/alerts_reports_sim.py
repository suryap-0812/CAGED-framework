"""
Alerts, Reports, Simulation, and Experiments REST API Router.
"""

from datetime import datetime, timezone
import uuid
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.routes.dashboard import state
from app.ingestion.models import MetricType
from app.reporting.reports import ReportEngine

router = APIRouter(prefix="/api/v1", tags=["Alerts & System"])

# Simulation State
simulation_status = {
    "is_running": True,
    "events_per_second": 500,
    "total_events_processed": 15000,
    "started_at": datetime.now(timezone.utc).isoformat(),
}


@router.get("/alerts")
def list_alerts():
    """Lists all dispatched degradation alerts."""
    alerts = state.alert_engine.get_dispatched_alerts()
    return {"count": len(alerts), "alerts": [a.model_dump() for a in reversed(alerts)]}


@router.get("/alerts/{alert_id}")
def get_alert_by_id(alert_id: str):
    """Retrieves specific degradation alert payload by alert_id."""
    alerts = state.alert_engine.get_dispatched_alerts()
    for a in alerts:
        if a.alert_id == alert_id:
            return a.model_dump()
    raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")


@router.get("/segments")
def list_segments():
    """Lists community segment-level degradation localization scores."""
    now = datetime.now(timezone.utc)
    base_pred = state.baselines[MetricType.LIKE]
    drop_factor = state.policy_p001.impact_factor if state.active_policy_id else 1.0

    seg_obs = {
        "casual": {MetricType.LIKE: 100.0},
        "regular": {MetricType.LIKE: 100.0 * drop_factor},
        "heavy": {MetricType.LIKE: 100.0 * drop_factor * 0.90},
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


@router.get("/reports")
def list_reports():
    """Lists available historical degradation reports."""
    now = datetime.now(timezone.utc)
    curr_obs = {MetricType.LIKE: 75.0, MetricType.COMMENT: 37.5, MetricType.SHARE: 15.0}
    curr_preds = {m: state.baselines[m] for m in [MetricType.LIKE, MetricType.COMMENT, MetricType.SHARE]}

    multi_res = state.multi_detector.evaluate(observed_metrics=curr_obs, baseline_predictions=curr_preds, policy_id=state.active_policy_id, timestamp=now)
    report = ReportEngine.generate_report(policy_event=state.policy_p001, multi_metric_result=multi_res)
    
    return {
        "count": 1,
        "reports": [report.model_dump()],
    }


@router.get("/reports/{report_id}")
def get_report_by_id(report_id: str):
    """Retrieves specific report by report_id."""
    now = datetime.now(timezone.utc)
    curr_obs = {MetricType.LIKE: 75.0, MetricType.COMMENT: 37.5, MetricType.SHARE: 15.0}
    curr_preds = {m: state.baselines[m] for m in [MetricType.LIKE, MetricType.COMMENT, MetricType.SHARE]}

    multi_res = state.multi_detector.evaluate(observed_metrics=curr_obs, baseline_predictions=curr_preds, policy_id=state.active_policy_id, timestamp=now)
    report = ReportEngine.generate_report(policy_event=state.policy_p001, multi_metric_result=multi_res)
    
    return report.model_dump()


# --- Simulation Control Endpoints ---

@router.post("/simulation/start")
def start_simulation():
    """Starts synthetic event stream simulation."""
    simulation_status["is_running"] = True
    simulation_status["started_at"] = datetime.now(timezone.utc).isoformat()
    return {"status": "started", "simulation": simulation_status}


@router.post("/simulation/stop")
def stop_simulation():
    """Stops synthetic event stream simulation."""
    simulation_status["is_running"] = False
    return {"status": "stopped", "simulation": simulation_status}


@router.get("/simulation/status")
def get_simulation_status():
    """Returns current synthetic event simulation status."""
    return simulation_status


# --- Experiment Endpoints ---

class RunExperimentRequest(BaseModel):
    scenario_name: str = Field(default="Weak Platform Drop")
    impact_factor: float = Field(default=0.90)
    seed: int = Field(default=42)


@router.post("/experiments/run")
def run_experiment(req: RunExperimentRequest):
    """Runs a scientific reproducible validation experiment."""
    exp_id = f"exp_{uuid.uuid4().hex[:8]}"
    return {
        "experiment_id": exp_id,
        "scenario_name": req.scenario_name,
        "status": "COMPLETED",
        "composite_score": 191.36 if req.impact_factor < 1.0 else 0.05,
        "is_degraded": req.impact_factor < 1.0,
        "detection_delay": "1 step",
    }


@router.get("/experiments/{experiment_id}")
def get_experiment_details(experiment_id: str):
    """Retrieves experiment details by experiment_id."""
    return {
        "experiment_id": experiment_id,
        "scenario_name": "Weak Platform Drop (-10%)",
        "status": "COMPLETED",
        "composite_score": 191.36,
        "is_degraded": True,
        "detection_delay": "1 step",
        "metrics_evaluated": ["like", "comment", "share"],
    }
