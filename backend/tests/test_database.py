"""
Unit Tests for Phase 21 Database Persistence and ORM Models.
"""

from datetime import datetime, timezone
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.baselines.snapshot import BaselineSnapshot
from app.db.models import Base
from app.db.repository import CAGEDRepository
from app.ingestion.models import MetricType
from app.policy.models import PolicyEvent
from app.preprocessing.privacy import FORBIDDEN_FIELDS
from app.reporting.alerts import AlertSeverity, DegradationAlert
from app.reporting.reports import DegradationReport, MetricReportItem, ReportEngine


@pytest.fixture
def db_session():
    """In-memory SQLite database session fixture for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_db_policy_event_persistence(db_session):
    """Tests saving and loading PolicyEventDB entries."""
    repo = CAGEDRepository(db_session)

    policy = PolicyEvent(
        policy_id="P_DB_001",
        policy_name="DB Test Policy",
        timestamp=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
        description="Testing ORM persistence",
        impact_factor=0.75,
    )

    repo.save_policy_event(policy)

    events = repo.list_policy_events()
    assert len(events) == 1
    assert events[0].policy_id == "P_DB_001"
    assert events[0].impact_factor == 0.75


def test_db_baseline_snapshot_persistence(db_session):
    """Tests saving and retrieving BaselineSnapshotDB entries."""
    repo = CAGEDRepository(db_session)

    snapshot = BaselineSnapshot(
        snapshot_id="snap_P_DB_001_like",
        policy_id="P_DB_001",
        metric_type=MetricType.LIKE,
        frozen_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
        model_type="exponential_smoothing",
        model_state={"level": 100.0, "trend": 0.0},
    )

    repo.save_baseline_snapshot(snapshot)

    db_snap = repo.get_baseline_snapshot("snap_P_DB_001_like")
    assert db_snap is not None
    assert db_snap.policy_id == "P_DB_001"
    
    state_dict = json.loads(db_snap.model_state_json)
    assert state_dict["level"] == 100.0


def test_db_alert_and_report_persistence(db_session):
    """Tests saving DegradationAlertDB and DegradationReportDB entries."""
    repo = CAGEDRepository(db_session)

    alert = DegradationAlert(
        policy_id="P_DB_001",
        timestamp=datetime.now(timezone.utc),
        severity=AlertSeverity.CRITICAL,
        metric_types=[MetricType.LIKE],
        composite_score=25.0,
        max_z_score=5.0,
        p_value=0.0001,
        message="Critical engagement drop detected",
    )

    repo.save_alert(alert)

    alerts = repo.list_alerts()
    assert len(alerts) == 1
    assert alerts[0].severity == "CRITICAL"
    assert alerts[0].composite_score == 25.0

    report = DegradationReport(
        generated_at=datetime.now(timezone.utc),
        policy_id="P_DB_001",
        policy_name="DB Test",
        policy_description="Desc",
        policy_timestamp=datetime.now(timezone.utc),
        overall_composite_score=25.0,
        overall_is_degraded=True,
        affected_metrics=[],
        segment_breakdown=[],
    )

    repo.save_report(report, markdown_content="# CAGED Test Report")

    reports = repo.list_reports()
    assert len(reports) == 1
    assert reports[0].policy_id == "P_DB_001"
    assert reports[0].overall_is_degraded is True


def test_db_zero_private_content_stored(db_session):
    """
    CRITICAL PRIVACY TEST: Confirms no forbidden private fields exist in any ORM model schemas.
    """
    for table_name, table in Base.metadata.tables.items():
        for column in table.columns:
            assert column.name not in FORBIDDEN_FIELDS
