"""
Policies REST API Router.
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.routes.dashboard import state
from app.ingestion.models import MetricType
from app.policy.models import PolicyEvent
from app.simulation.user_profile import UserSegment

router = APIRouter(prefix="/api/v1/policies", tags=["Policies"])


class CreatePolicyRequest(BaseModel):
    policy_id: str = Field(..., min_length=1, description="Policy identifier e.g. P002")
    policy_name: str = Field(..., min_length=1, description="Human readable title")
    timestamp: Optional[datetime] = Field(default=None, description="T0 timestamp")
    description: str = Field(..., min_length=1, description="Policy change summary")
    target_metric: Optional[MetricType] = Field(default=None)
    target_segment: Optional[UserSegment] = Field(default=None)
    impact_factor: float = Field(default=0.80, ge=0.0, le=2.0)


@router.get("")
def list_policies():
    """Lists all registered policy events."""
    events = state.timeline.get_all_policy_events()
    return {
        "count": len(events),
        "active_policy_id": state.active_policy_id,
        "policies": [e.model_dump() for e in events],
    }


@router.post("")
def create_policy(req: CreatePolicyRequest):
    """Registers a new policy change event at T0."""
    t_val = req.timestamp or datetime.now(timezone.utc)
    if t_val.tzinfo is None:
        t_val = t_val.replace(tzinfo=timezone.utc)

    event = PolicyEvent(
        policy_id=req.policy_id,
        policy_name=req.policy_name,
        timestamp=t_val,
        description=req.description,
        target_metric=req.target_metric,
        target_segment=req.target_segment,
        impact_factor=req.impact_factor,
    )

    state.timeline.add_policy_event(event)
    state.policy_p001 = event
    state.t0 = t_val
    state.active_policy_id = req.policy_id

    return {
        "status": "success",
        "policy": event.model_dump(),
    }


@router.get("/{policy_id}")
def get_policy(policy_id: str):
    """Retrieves specific policy event details by policy_id."""
    events = state.timeline.get_all_policy_events()
    for e in events:
        if e.policy_id == policy_id:
            return e.model_dump()
    raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found.")
