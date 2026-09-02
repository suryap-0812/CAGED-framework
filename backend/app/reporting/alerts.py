"""
Alert Engine with Severity Routing and Deduplication Suppression Windows.
"""

from datetime import datetime, timezone
from enum import Enum
import uuid
from typing import Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.detection.multi_metric import MultiMetricDegradationResult
from app.detection.segment_metric import SegmentComparisonReport
from app.ingestion.models import MetricType
from app.ml.predictor import MLPredictionResult

logger = get_logger(__name__)


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class DegradationAlert(BaseModel):
    """Container for degradation alert payload."""

    alert_id: str = Field(default_factory=lambda: f"alt_{uuid.uuid4().hex[:10]}")
    policy_id: Optional[str] = Field(default=None, description="Associated policy identifier")
    timestamp: datetime = Field(..., description="UTC timestamp of alert trigger")
    severity: AlertSeverity = Field(..., description="Alert severity level")
    metric_types: List[MetricType] = Field(..., description="List of degraded engagement metrics")
    composite_score: float = Field(..., description="Multi-metric composite score S")
    max_z_score: float = Field(..., description="Highest Z-score deviation among metrics")
    p_value: float = Field(..., description="One-tailed p-value")
    most_degraded_segment: Optional[str] = Field(default=None, description="Segment ID with highest degradation")
    message: str = Field(..., description="Human-readable alert message")
    ml_early_warning: Optional[Dict] = Field(default=None, description="Optional ML early-warning metadata")


class AlertEngine:
    """
    Manages degradation alert evaluation, severity classification, deduplication,
    and alert fatigue suppression windows.
    """

    def __init__(self, suppression_window_seconds: int = 300):
        """
        Args:
            suppression_window_seconds: Alert suppression window duration (default: 300s / 5 mins).
        """
        self.suppression_window_seconds = suppression_window_seconds
        # Maps alert_key (policy_id + segment_id) -> Tuple[last_alert_time, last_severity]
        self._last_alert_history: Dict[str, Tuple[datetime, AlertSeverity]] = {}
        self._dispatched_alerts: List[DegradationAlert] = []
        self._listeners: List[Callable[[DegradationAlert], None]] = []

    def register_listener(self, callback: Callable[[DegradationAlert], None]) -> None:
        """Registers listener callback for dispatched alerts."""
        self._listeners.append(callback)

    def evaluate_and_alert(
        self,
        multi_metric_result: MultiMetricDegradationResult,
        segment_report: Optional[SegmentComparisonReport] = None,
        ml_result: Optional[MLPredictionResult] = None,
        policy_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> Optional[DegradationAlert]:
        """
        Evaluates metrics and dispatches alert if degradation occurs and isn't suppressed.
        """
        eval_time = timestamp or datetime.now(timezone.utc)
        if eval_time.tzinfo is None:
            eval_time = eval_time.replace(tzinfo=timezone.utc)

        pol_id = policy_id or multi_metric_result.policy_id

        # Determine if overall or segment degradation is present
        is_degraded = multi_metric_result.is_degraded or (
            segment_report and any(s.is_degraded for s in segment_report.segment_results.values())
        )

        if not is_degraded:
            return None

        # Calculate max Z-score across metrics
        max_z = 0.0
        degraded_metrics: List[MetricType] = []
        min_p_val = 1.0

        for m_str, m_res in multi_metric_result.metric_results.items():
            if m_res.positive_z_score > max_z:
                max_z = m_res.positive_z_score
            if m_res.p_value < min_p_val:
                min_p_val = m_res.p_value
            if m_res.is_degraded:
                degraded_metrics.append(MetricType(m_str))

        comp_score = multi_metric_result.composite_score

        # Determine Severity Level
        if comp_score >= 15.0 or max_z >= 4.0:
            severity = AlertSeverity.CRITICAL
        elif comp_score >= 6.0 or max_z >= 2.5:
            severity = AlertSeverity.WARNING
        else:
            severity = AlertSeverity.INFO

        # Key for alert deduplication
        most_deg_seg = segment_report.most_degraded_segment if segment_report else None
        alert_key = f"{pol_id or 'global'}_{most_deg_seg or 'platform'}"

        # Check Suppression Window / Alert Fatigue
        if alert_key in self._last_alert_history:
            last_time, last_sev = self._last_alert_history[alert_key]
            elapsed_sec = (eval_time - last_time).total_seconds()

            # Suppress if within window AND severity has not escalated
            if elapsed_sec < self.suppression_window_seconds and not self._is_severity_escalation(last_sev, severity):
                logger.info(
                    "Alert suppressed for key '%s' (elapsed %.1fs < %ds, sev %s <= %s)",
                    alert_key, elapsed_sec, self.suppression_window_seconds, severity.value, last_sev.value
                )
                return None

        # Build Alert Message
        metrics_str = ", ".join([m.value.upper() for m in degraded_metrics]) or "COMPOSITE"
        seg_str = f" in segment '{most_deg_seg}'" if most_deg_seg else ""
        msg = f"[{severity.value}] Engagement degradation detected{seg_str} on [{metrics_str}]. Composite Score S=%.2f, Max Z=%.2f, p=%.4f" % (
            comp_score, max_z, min_p_val
        )

        ml_dict = ml_result.model_dump() if ml_result else None

        alert = DegradationAlert(
            policy_id=pol_id,
            timestamp=eval_time,
            severity=severity,
            metric_types=degraded_metrics,
            composite_score=comp_score,
            max_z_score=max_z,
            p_value=min_p_val,
            most_degraded_segment=most_deg_seg,
            message=msg,
            ml_early_warning=ml_dict,
        )

        # Record history & dispatch to listeners
        self._last_alert_history[alert_key] = (eval_time, severity)
        self._dispatched_alerts.append(alert)

        for listener in self._listeners:
            try:
                listener(alert)
            except Exception as err:
                logger.error("Alert listener callback failed: %s", str(err))

        logger.warning("DISPATCHED ALERT: %s", msg)
        return alert

    def _is_severity_escalation(self, previous: AlertSeverity, current: AlertSeverity) -> bool:
        sev_rank = {AlertSeverity.INFO: 1, AlertSeverity.WARNING: 2, AlertSeverity.CRITICAL: 3}
        return sev_rank[current] > sev_rank[previous]

    def get_dispatched_alerts(self) -> List[DegradationAlert]:
        return list(self._dispatched_alerts)

    def clear_history() -> None:
        self._last_alert_history.clear()
        self._dispatched_alerts.clear()
