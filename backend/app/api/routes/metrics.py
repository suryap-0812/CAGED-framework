"""
Metrics REST API Router.
"""

from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.api.routes.dashboard import state
from app.ingestion.models import MetricType

router = APIRouter(prefix="/api/v1", tags=["Metrics"])


@router.get("/metrics")
def list_all_metrics():
    """Returns list of active monitored metrics and current observed values."""
    metrics_list = []
    for m in MetricType:
        if m in state.baselines:
            pred = state.baselines[m]
            metrics_list.append({
                "metric_type": m.value,
                "expected_value": pred.expected_value,
                "variance": pred.variance,
                "std_dev": pred.std_dev,
                "ci_lower": pred.ci_lower,
                "ci_upper": pred.ci_upper,
            })
    return {"count": len(metrics_list), "metrics": metrics_list}


@router.get("/metrics/{metric}")
def get_metric_detail(metric: str):
    """Returns metric details for a specific metric type."""
    try:
        m_enum = MetricType(metric.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid metric '{metric}'.")

    if m_enum not in state.baselines:
        raise HTTPException(status_code=440, detail=f"Metric '{metric}' not initialized.")

    pred = state.baselines[m_enum]
    return {
        "metric_type": m_enum.value,
        "expected_value": pred.expected_value,
        "variance": pred.variance,
        "std_dev": pred.std_dev,
        "ci_lower": pred.ci_lower,
        "ci_upper": pred.ci_upper,
    }


@router.get("/baseline/{metric}")
def get_baseline_for_metric(metric: str):
    """Returns pre-policy frozen baseline parameters for a given metric."""
    try:
        m_enum = MetricType(metric.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid metric '{metric}'.")

    if not state.active_policy_id:
        raise HTTPException(status_code=404, detail="No active policy frozen baseline found.")

    try:
        frozen_model = state.snapshotter.get_frozen_model(state.active_policy_id, m_enum)
        pred = frozen_model.predict()
        return {
            "policy_id": state.active_policy_id,
            "metric_type": m_enum.value,
            "expected_value": pred.expected_value,
            "std_dev": pred.std_dev,
            "ci_lower": pred.ci_lower,
            "ci_upper": pred.ci_upper,
        }
    except Exception:
        # Fallback to current baseline if snapshotter is empty
        pred = state.baselines.get(m_enum)
        if not pred:
            raise HTTPException(status_code=404, detail=f"No baseline available for {metric}.")
        return {
            "policy_id": state.active_policy_id,
            "metric_type": m_enum.value,
            "expected_value": pred.expected_value,
            "std_dev": pred.std_dev,
            "ci_lower": pred.ci_lower,
            "ci_upper": pred.ci_upper,
        }
