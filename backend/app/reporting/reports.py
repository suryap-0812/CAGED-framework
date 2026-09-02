"""
Report Engine Generating JSON and Markdown Causal Engagement Degradation Reports.
"""

from datetime import datetime, timezone
import json
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.detection.multi_metric import MultiMetricDegradationResult
from app.detection.segment_metric import SegmentComparisonReport
from app.ingestion.models import MetricType
from app.ml.predictor import MLPredictionResult
from app.policy.models import PolicyEvent


class MetricReportItem(BaseModel):
    metric_type: str
    expected_value: float
    observed_value: float
    deviation: float
    z_score: float
    positive_z_score: float
    p_value: float
    is_degraded: bool
    status: str


class SegmentReportItem(BaseModel):
    segment_id: str
    composite_score: float
    is_degraded: bool
    top_degraded_metric: Optional[str]


class DegradationReport(BaseModel):
    """Structured Causal Engagement Degradation Report Container."""

    report_id: str = Field(default_factory=lambda: f"rep_{uuid.uuid4().hex[:10]}")
    generated_at: datetime = Field(..., description="UTC timestamp of report generation")
    policy_id: str = Field(..., description="Policy identifier")
    policy_name: str = Field(..., description="Policy title")
    policy_description: str = Field(..., description="Policy summary description")
    policy_timestamp: datetime = Field(..., description="Policy trigger timestamp T0")
    overall_composite_score: float = Field(..., description="Overall multi-metric composite score S")
    overall_is_degraded: bool = Field(..., description="Platform-wide degradation status")
    affected_metrics: List[MetricReportItem] = Field(..., description="Metric-level degradation details")
    segment_breakdown: List[SegmentReportItem] = Field(..., description="Segment-level localization details")
    most_degraded_segment: Optional[str] = Field(default=None, description="Most affected user segment")
    least_degraded_segment: Optional[str] = Field(default=None, description="Least affected user segment")
    is_localized: bool = Field(default=False, description="True if degradation is concentrated in segment(s)")
    ml_early_warning: Optional[Dict[str, Any]] = Field(default=None, description="Optional ML early-warning metadata")


class ReportEngine:
    """Engine compiling and formatting CAGED Causal Degradation Reports."""

    @classmethod
    def generate_report(
        cls,
        policy_event: PolicyEvent,
        multi_metric_result: MultiMetricDegradationResult,
        segment_report: Optional[SegmentComparisonReport] = None,
        ml_result: Optional[MLPredictionResult] = None,
        generated_at: Optional[datetime] = None,
    ) -> DegradationReport:
        """Compiles a complete DegradationReport instance."""
        now_time = generated_at or datetime.now(timezone.utc)
        if now_time.tzinfo is None:
            now_time = now_time.replace(tzinfo=timezone.utc)

        # Build metric items
        metric_items: List[MetricReportItem] = []
        for m_str, m_res in multi_metric_result.metric_results.items():
            metric_items.append(
                MetricReportItem(
                    metric_type=m_str,
                    expected_value=m_res.expected_value,
                    observed_value=m_res.observed_value,
                    deviation=m_res.deviation,
                    z_score=m_res.z_score,
                    positive_z_score=m_res.positive_z_score,
                    p_value=m_res.p_value,
                    is_degraded=m_res.is_degraded,
                    status=m_res.status,
                )
            )

        # Build segment items
        segment_items: List[SegmentReportItem] = []
        most_deg_seg = None
        least_deg_seg = None
        is_loc = False

        if segment_report:
            most_deg_seg = segment_report.most_degraded_segment
            least_deg_seg = segment_report.least_degraded_segment
            is_loc = segment_report.is_localized

            for seg_id, seg_res in segment_report.segment_results.items():
                top_m = seg_res.top_degraded_metric.value if seg_res.top_degraded_metric else None
                segment_items.append(
                    SegmentReportItem(
                        segment_id=seg_id,
                        composite_score=seg_res.composite_score,
                        is_degraded=seg_res.is_degraded,
                        top_degraded_metric=top_m,
                    )
                )

        ml_dict = ml_result.model_dump() if ml_result else None

        return DegradationReport(
            generated_at=now_time,
            policy_id=policy_event.policy_id,
            policy_name=policy_event.policy_name,
            policy_description=policy_event.description,
            policy_timestamp=policy_event.timestamp,
            overall_composite_score=multi_metric_result.composite_score,
            overall_is_degraded=multi_metric_result.is_degraded,
            affected_metrics=metric_items,
            segment_breakdown=segment_items,
            most_degraded_segment=most_deg_seg,
            least_degraded_segment=least_deg_seg,
            is_localized=is_loc,
            ml_early_warning=ml_dict,
        )

    @classmethod
    def export_json(cls, report: DegradationReport) -> str:
        """Serializes report to formatted JSON string."""
        return report.model_dump_json(indent=2)

    @classmethod
    def export_markdown(cls, report: DegradationReport) -> str:
        """Formats report as publication-ready GitHub-flavored Markdown."""
        deg_badge = "🚨 **DEGRADED**" if report.overall_is_degraded else "✅ **STABLE**"
        loc_badge = "🎯 **LOCALIZED IMPACT**" if report.is_localized else "🌐 **UNIFORM IMPACT**"

        lines = [
            f"# CAGED Causal Engagement Degradation Report",
            f"**Report ID**: `{report.report_id}` | **Generated**: `{report.generated_at.isoformat()}`",
            "",
            f"## Executive Summary",
            f"- **Overall Platform Status**: {deg_badge}",
            f"- **Composite Degradation Score (S)**: `{report.overall_composite_score:.2f}`",
            f"- **Impact Scope**: {loc_badge}",
            f"- **Target Policy ID**: `{report.policy_id}` — *{report.policy_name}*",
            f"- **Policy Enacted At (T0)**: `{report.policy_timestamp.isoformat()}`",
            "",
            f"## Policy Event Context",
            f"> {report.policy_description}",
            "",
            f"## Metric-Level Degradation Analysis",
            f"| Metric | Expected (E) | Observed (O) | Deviation (D) | Z-Score | p-value | Status |",
            f"| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]

        for item in report.affected_metrics:
            status_symbol = "🔴 DEGRADED" if item.is_degraded else "🟢 STABLE"
            lines.append(
                f"| `{item.metric_type.upper()}` | `{item.expected_value:.2f}` | `{item.observed_value:.2f}` | `{item.deviation:+.2f}` | `{item.z_score:+.2f}` | `{item.p_value:.4f}` | {status_symbol} |"
            )

        if report.segment_breakdown:
            lines.extend([
                "",
                f"## User Segment Localization",
                f"- **Most Degraded Segment**: `{report.most_degraded_segment or 'N/A'}`",
                f"- **Least Degraded Segment**: `{report.least_degraded_segment or 'N/A'}`",
                "",
                f"| Segment ID | Composite Score (S_s) | Status | Top Degraded Metric |",
                f"| :--- | :---: | :---: | :--- |",
            ])
            for seg in report.segment_breakdown:
                s_symbol = "🔴 DEGRADED" if seg.is_degraded else "🟢 STABLE"
                lines.append(
                    f"| `{seg.segment_id}` | `{seg.composite_score:.2f}` | {s_symbol} | `{seg.top_degraded_metric or 'None'}` |"
                )

        if report.ml_early_warning:
            ml_data = report.ml_early_warning
            prob = ml_data.get("degradation_probability", 0.0)
            status = ml_data.get("warning_status", "NORMAL")
            horizon = ml_data.get("prediction_horizon_minutes", 15)
            lines.extend([
                "",
                f"## ML Early-Warning Forecast ({horizon}m Horizon)",
                f"- **Predicted Degradation Probability**: `{prob * 100.0:.1f}%`",
                f"- **Warning Level**: `{status}`",
            ])

        lines.extend([
            "",
            "---",
            "*Generated by CAGED (Causal Analysis for Guaranteed Engagement Degradation)*",
        ])

        return "\n".join(lines)
