"""
Repository CRUD Operations for Persistent CAGED Analytical Store.
"""

import json
from typing import List, Optional
from sqlalchemy.orm import Session

from app.baselines.snapshot import BaselineSnapshot
from app.db.models import (
    BaselineSnapshotDB,
    DegradationAlertDB,
    DegradationReportDB,
    ExperimentDB,
    PolicyEventDB,
)
from app.policy.models import PolicyEvent
from app.reporting.alerts import DegradationAlert
from app.reporting.reports import DegradationReport


class CAGEDRepository:
    """Repository service managing database operations for CAGED analytical state."""

    def __init__(self, db_session: Session):
        self.db = db_session

    # --- Policy Events ---

    def save_policy_event(self, policy: PolicyEvent) -> PolicyEventDB:
        """Persists a PolicyEvent to database."""
        db_item = PolicyEventDB(
            policy_id=policy.policy_id,
            policy_name=policy.policy_name,
            timestamp=policy.timestamp,
            description=policy.description,
            impact_factor=policy.impact_factor,
            target_metric=policy.target_metric.value if policy.target_metric else None,
            target_segment=policy.target_segment.value if policy.target_segment else None,
        )
        self.db.merge(db_item)
        self.db.commit()
        return db_item

    def list_policy_events(self) -> List[PolicyEventDB]:
        """Lists all persisted policy events."""
        return self.db.query(PolicyEventDB).order_by(PolicyEventDB.timestamp.asc()).all()

    # --- Baseline Snapshots ---

    def save_baseline_snapshot(self, snapshot: BaselineSnapshot) -> BaselineSnapshotDB:
        """Persists a BaselineSnapshot to database."""
        db_item = BaselineSnapshotDB(
            snapshot_id=snapshot.snapshot_id,
            policy_id=snapshot.policy_id,
            metric_type=snapshot.metric_type.value,
            frozen_at=snapshot.frozen_at,
            model_type=snapshot.model_type,
            model_state_json=json.dumps(snapshot.model_state),
        )
        self.db.merge(db_item)
        self.db.commit()
        return db_item

    def get_baseline_snapshot(self, snapshot_id: str) -> Optional[BaselineSnapshotDB]:
        """Retrieves a baseline snapshot by snapshot_id."""
        return self.db.query(BaselineSnapshotDB).filter_by(snapshot_id=snapshot_id).first()

    # --- Alerts ---

    def save_alert(self, alert: DegradationAlert) -> DegradationAlertDB:
        """Persists a DegradationAlert to database."""
        db_item = DegradationAlertDB(
            alert_id=alert.alert_id,
            policy_id=alert.policy_id,
            timestamp=alert.timestamp,
            severity=alert.severity.value,
            composite_score=alert.composite_score,
            max_z_score=alert.max_z_score,
            p_value=alert.p_value,
            most_degraded_segment=alert.most_degraded_segment,
            message=alert.message,
        )
        self.db.merge(db_item)
        self.db.commit()
        return db_item

    def list_alerts(self, limit: int = 50) -> List[DegradationAlertDB]:
        """Lists recent alerts ordered by timestamp descending."""
        return self.db.query(DegradationAlertDB).order_by(DegradationAlertDB.timestamp.desc()).limit(limit).all()

    # --- Reports ---

    def save_report(self, report: DegradationReport, markdown_content: str = "") -> DegradationReportDB:
        """Persists a DegradationReport to database."""
        db_item = DegradationReportDB(
            report_id=report.report_id,
            policy_id=report.policy_id,
            generated_at=report.generated_at,
            overall_composite_score=report.overall_composite_score,
            overall_is_degraded=report.overall_is_degraded,
            is_localized=report.is_localized,
            report_json=report.model_dump_json(),
            markdown_content=markdown_content,
        )
        self.db.merge(db_item)
        self.db.commit()
        return db_item

    def list_reports(self) -> List[DegradationReportDB]:
        """Lists all persisted degradation reports."""
        return self.db.query(DegradationReportDB).order_by(DegradationReportDB.generated_at.desc()).all()

    # --- Experiments ---

    def save_experiment(
        self, experiment_id: str, scenario_name: str, composite_score: float, is_degraded: bool
    ) -> ExperimentDB:
        """Persists an ExperimentDB entry to database."""
        db_item = ExperimentDB(
            experiment_id=experiment_id,
            scenario_name=scenario_name,
            timestamp=PolicyEventDB.timestamp.type.python_type.now(),
            composite_score=composite_score,
            is_degraded=is_degraded,
            status="COMPLETED",
        )
        self.db.merge(db_item)
        self.db.commit()
        return db_item
