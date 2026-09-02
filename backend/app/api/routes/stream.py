"""
Server-Sent Events (SSE) Real-Time Streaming Router for CAGED Dashboard.
"""

import asyncio
from datetime import datetime, timezone
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.routes.dashboard import state
from app.ingestion.models import MetricType

router = APIRouter(prefix="/api/v1/dashboard", tags=["Stream"])


async def sse_event_generator():
    """Yields real-time Server-Sent Events (SSE) data stream every 1 second."""
    step = 0
    while True:
        step += 1
        now = datetime.now(timezone.utc)
        
        # Calculate current real-time stream state
        drop_factor = state.policy_p001.impact_factor if state.active_policy_id else 1.0
        noise = (step % 5 - 2.0) * 0.5

        like_obs = round(100.0 * drop_factor + noise, 2)
        comment_obs = round(50.0 * drop_factor + noise * 0.5, 2)
        share_obs = round(20.0 * drop_factor + noise * 0.2, 2)

        curr_obs = {
            MetricType.LIKE: like_obs,
            MetricType.COMMENT: comment_obs,
            MetricType.SHARE: share_obs,
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

        alert = state.alert_engine.evaluate_and_alert(
            multi_metric_result=multi_res,
            policy_id=state.active_policy_id,
            timestamp=now,
        )

        sse_data = {
            "step": step,
            "timestamp": now.isoformat(),
            "policy_t0": state.t0.isoformat(),
            "active_policy_id": state.active_policy_id,
            "composite_score": multi_res.composite_score,
            "composite_threshold": multi_res.composite_threshold,
            "is_degraded": multi_res.is_degraded,
            "top_contributor": multi_res.top_contributor.value if multi_res.top_contributor else None,
            "metrics": {
                "like": {"observed": like_obs, "expected": 100.0, "z_score": multi_res.metric_results.get("like", {}).positive_z_score if hasattr(multi_res.metric_results.get("like"), "positive_z_score") else 0.0},
                "comment": {"observed": comment_obs, "expected": 50.0, "z_score": multi_res.metric_results.get("comment", {}).positive_z_score if hasattr(multi_res.metric_results.get("comment"), "positive_z_score") else 0.0},
                "share": {"observed": share_obs, "expected": 20.0, "z_score": multi_res.metric_results.get("share", {}).positive_z_score if hasattr(multi_res.metric_results.get("share"), "positive_z_score") else 0.0},
            },
            "latest_alert": alert.model_dump(mode="json") if alert else None,
        }

        yield f"data: {json.dumps(sse_data)}\n\n"
        await asyncio.sleep(1.0)


@router.get("/stream")
async def stream_dashboard_events():
    """
    Server-Sent Events (SSE) endpoint pushing real-time engagement streams and alert updates.
    """
    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
