"""
Pre-Policy Baseline Freezing & Counterfactual Snapshotting Engine.
"""

import copy
from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.baselines.arima_baseline import ARIMABaseline
from app.baselines.base import BaselineModel
from app.baselines.exponential_smoothing import ExponentialSmoothingBaseline
from app.baselines.snapshot import BaselineSnapshot
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import get_logger
from app.ingestion.models import MetricType

logger = get_logger(__name__)


class BaselineSnapshotter:
    """
    Manages freezing, storage, and restoration of pre-policy counterfactual baseline models.
    """

    def __init__(self):
        # Maps snapshot_id -> BaselineSnapshot metadata
        self._snapshots: Dict[str, BaselineSnapshot] = {}
        # Maps snapshot_id -> restored immutable BaselineModel instance
        self._frozen_models: Dict[str, BaselineModel] = {}

    def freeze_baseline(
        self,
        policy_id: str,
        metric: MetricType,
        baseline_model: BaselineModel,
        frozen_at: Optional[datetime] = None,
        segment: Optional[str] = None,
    ) -> BaselineSnapshot:
        """
        Freezes the current state of a baseline model at policy trigger time T0.
        
        Args:
            policy_id: Policy ID trigger (e.g. P001).
            metric: Target metric type.
            baseline_model: Active baseline model instance to freeze.
            frozen_at: Optional UTC timestamp (defaults to current time).
            segment: Optional segment label.
            
        Returns:
            BaselineSnapshot instance.
        """
        snapshot_id = BaselineSnapshot.create_snapshot_id(policy_id, metric, segment)
        t_freeze = frozen_at or datetime.now(timezone.utc)
        if t_freeze.tzinfo is None:
            t_freeze = t_freeze.replace(tzinfo=timezone.utc)

        # Deep-copy the active model to guarantee complete isolation from future updates
        frozen_copy = copy.deepcopy(baseline_model)

        # Serialize model parameters
        if isinstance(baseline_model, ExponentialSmoothingBaseline):
            model_type = "exponential_smoothing"
            state = {
                "alpha": baseline_model.alpha,
                "beta": baseline_model.beta,
                "gamma": baseline_model.gamma,
                "seasonal_period": baseline_model.seasonal_period,
                "level": baseline_model.level,
                "trend": baseline_model.trend,
                "seasonals": list(baseline_model.seasonals),
                "residuals": list(baseline_model.residuals),
                "is_fitted": baseline_model.is_fitted,
                "step_counter": baseline_model._step_counter,
            }
        elif isinstance(baseline_model, ARIMABaseline):
            model_type = "arima"
            state = {
                "p_order": baseline_model.p_order,
                "intercept": baseline_model.intercept,
                "phi": baseline_model.phi.tolist(),
                "history": list(baseline_model.history),
                "residuals": list(baseline_model.residuals),
                "is_fitted": baseline_model.is_fitted,
            }
        else:
            model_type = "generic"
            state = {}

        snapshot = BaselineSnapshot(
            snapshot_id=snapshot_id,
            policy_id=policy_id,
            metric_type=metric,
            frozen_at=t_freeze,
            model_type=model_type,
            model_state=state,
            segment=segment,
        )

        self._snapshots[snapshot_id] = snapshot
        self._frozen_models[snapshot_id] = frozen_copy

        logger.info(
            "Frozen Pre-Policy Baseline '%s' for policy %s at %s (level=%.2f, trend=%.4f)",
            snapshot_id, policy_id, t_freeze.isoformat(), getattr(frozen_copy, 'level', 0.0), getattr(frozen_copy, 'trend', 0.0)
        )
        return snapshot

    def get_frozen_model(
        self, policy_id: str, metric: MetricType, segment: Optional[str] = None
    ) -> BaselineModel:
        """
        Retrieves the frozen, un-contaminated counterfactual baseline model for a policy and metric.
        """
        snapshot_id = BaselineSnapshot.create_snapshot_id(policy_id, metric, segment)
        if snapshot_id not in self._frozen_models:
            raise ResourceNotFoundException(
                f"Frozen baseline snapshot '{snapshot_id}' not found for policy '{policy_id}' and metric '{metric.value}'."
            )
        
        # Return a copy to ensure caller operations cannot alter stored snapshot
        return copy.deepcopy(self._frozen_models[snapshot_id])

    def get_snapshot_metadata(
        self, policy_id: str, metric: MetricType, segment: Optional[str] = None
    ) -> BaselineSnapshot:
        """Retrieves BaselineSnapshot metadata."""
        snapshot_id = BaselineSnapshot.create_snapshot_id(policy_id, metric, segment)
        if snapshot_id not in self._snapshots:
            raise ResourceNotFoundException(f"Snapshot '{snapshot_id}' not found.")
        return self._snapshots[snapshot_id]

    def list_snapshots(self, policy_id: Optional[str] = None) -> List[BaselineSnapshot]:
        """Returns list of snapshots, optionally filtered by policy_id."""
        if policy_id:
            return [s for s in self._snapshots.values() if s.policy_id == policy_id]
        return list(self._snapshots.values())

    def clear(self) -> None:
        """Clears all stored snapshots."""
        self._snapshots.clear()
        self._frozen_models.clear()
