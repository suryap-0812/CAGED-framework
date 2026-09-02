"""
Unit Tests for Alert Engine, Deduplication Window, and Report Engine.
"""

from datetime import datetime, timedelta, timezone
import json
import pytest

from app.baselines.base import BaselinePrediction
from app.detection.multi_metric import MultiMetricDetector
from app.detection.segment_metric import SegmentDegradationDetector
from app.ingestion.models import MetricType
from app.ml.predictor import MLPredictionResult
from app.policy.models import PolicyEvent
from app.reporting.alerts import AlertEngine, AlertSeverity, DegradationAlert
from app.reporting.reports import DegradationReport, ReportEngine


def test_alert_engine_trigger_and_listeners():
    """Verifies alert engine triggers alerts and executes listener callbacks."""
    engine = AlertEngine(suppression_window_seconds=300)
    
    received_alerts = []
    engine.register_listener(lambda alt: received_alerts.append(alt))

    detector = MultiMetricDetector()
    
    base_pred = BaselinePrediction(expected_value=100.0, std_dev=1.0, ci_lower=98.0, ci_upper=102.0)
    observed = {MetricType.LIKE: 90.0}  # Large drop -> Z = 10.0 -> S = 100.0 (CRITICAL)

    multi_res = detector.evaluate(observed_metrics=observed, baseline_predictions={MetricType.LIKE: base_pred}, policy_id="P001")

    alert = engine.evaluate_and_alert(multi_metric_result=multi_res, policy_id="P001")

    assert alert is not None
    assert alert.severity == AlertSeverity.CRITICAL
    assert alert.composite_score == 100.0
    assert alert.policy_id == "P001"

    # Confirms listener received the alert
    assert len(received_alerts) == 1
    assert received_alerts[0].alert_id == alert.alert_id


def test_alert_suppression_and_severity_escalation():
    """
    CRITICAL TEST: Ensures duplicate alerts are suppressed within the suppression window,
    but severity escalation immediately fires a new alert.
    """
    engine = AlertEngine(suppression_window_seconds=300)
    detector = MultiMetricDetector()
    base_pred = BaselinePrediction(expected_value=100.0, std_dev=1.0, ci_lower=98.0, ci_upper=102.0)

    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    # 1. First alert: Moderate drop (Z = 2.5 -> S = 6.25 -> WARNING)
    obs1 = {MetricType.LIKE: 97.5}
    res1 = detector.evaluate(observed_metrics=obs1, baseline_predictions={MetricType.LIKE: base_pred}, policy_id="P001")
    alert1 = engine.evaluate_and_alert(multi_metric_result=res1, timestamp=t0)

    assert alert1 is not None
    assert alert1.severity == AlertSeverity.WARNING

    # 2. Second alert 1 minute later with SAME severity -> SUPPRESSED!
    t1 = t0 + timedelta(minutes=1)
    alert2 = engine.evaluate_and_alert(multi_metric_result=res1, timestamp=t1)
    assert alert2 is None  # Suppressed!

    # 3. Third alert 2 minutes later with ESCALATED severity (Z = 5.0 -> S = 25.0 -> CRITICAL) -> DISPATCHED!
    t2 = t0 + timedelta(minutes=2)
    obs3 = {MetricType.LIKE: 95.0}
    res3 = detector.evaluate(observed_metrics=obs3, baseline_predictions={MetricType.LIKE: base_pred}, policy_id="P001")
    alert3 = engine.evaluate_and_alert(multi_metric_result=res3, timestamp=t2)

    assert alert3 is not None
    assert alert3.severity == AlertSeverity.CRITICAL


def test_report_engine_json_and_markdown_export():
    """Verifies complete report generation, JSON serialization, and Markdown formatting."""
    policy = PolicyEvent(
        policy_id="P001",
        policy_name="Strict Content Filter",
        timestamp=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        description="Applied stricter content filtering rule.",
    )

    multi_detector = MultiMetricDetector()
    base_pred = BaselinePrediction(expected_value=100.0, std_dev=1.0, ci_lower=98.0, ci_upper=102.0)
    observed = {MetricType.LIKE: 95.0, MetricType.COMMENT: 96.0}
    multi_res = multi_detector.evaluate(observed_metrics=observed, baseline_predictions={MetricType.LIKE: base_pred, MetricType.COMMENT: base_pred})

    seg_detector = SegmentDegradationDetector()
    seg_report = seg_detector.evaluate_all_segments(
        overall_observed=observed,
        overall_predictions={MetricType.LIKE: base_pred, MetricType.COMMENT: base_pred},
        segment_observed={"heavy": observed},
        segment_predictions={"heavy": {MetricType.LIKE: base_pred, MetricType.COMMENT: base_pred}},
    )

    ml_res = MLPredictionResult(
        timestamp=datetime.now(timezone.utc),
        prediction_horizon_minutes=15,
        degradation_probability=0.85,
        warning_status="CRITICAL",
    )

    report = ReportEngine.generate_report(
        policy_event=policy,
        multi_metric_result=multi_res,
        segment_report=seg_report,
        ml_result=ml_res,
    )

    assert isinstance(report, DegradationReport)
    assert report.policy_id == "P001"
    assert report.overall_is_degraded is True
    assert len(report.affected_metrics) == 2

    # JSON Export Verification
    json_str = ReportEngine.export_json(report)
    json_data = json.loads(json_str)
    assert json_data["policy_id"] == "P001"
    assert json_data["overall_is_degraded"] is True

    # Markdown Export Verification
    md_str = ReportEngine.export_markdown(report)
    assert "# CAGED Causal Engagement Degradation Report" in md_str
    assert "Strict Content Filter" in md_str
    assert "DEGRADED" in md_str
    assert "ML Early-Warning Forecast" in md_str
