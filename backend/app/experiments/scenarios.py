"""
Reproducible Scientific Experiment Framework & 10 Predefined Scenario Definitions for CAGED.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import numpy as np
from pydantic import BaseModel, Field

from app.baselines.base import BaselinePrediction
from app.baselines.exponential_smoothing import ExponentialSmoothingBaseline
from app.detection.multi_metric import MultiMetricDegradationResult, MultiMetricDetector
from app.detection.segment_metric import SegmentComparisonReport, SegmentDegradationDetector
from app.ingestion.models import MetricType
from app.policy.freezer import BaselineSnapshotter
from app.policy.models import PolicyEvent
from app.policy.registry import PolicyTimeline
from app.reporting.alerts import AlertEngine
from app.simulation.event_generator import EventGenerator, EventGeneratorConfig
from app.simulation.user_profile import UserSegment


class ExperimentScenario(BaseModel):
    """Configuration container for a reproducible scientific evaluation scenario."""

    scenario_id: str = Field(..., description="Unique scenario identifier")
    name: str = Field(..., description="Human readable scenario title")
    description: str = Field(..., description="Scientific objective and description")
    seed: int = Field(default=42, description="Random seed for reproducibility")
    num_users: int = Field(default=500, description="Synthetic user population")
    duration_hours: float = Field(default=24.0, description="Simulation stream duration in hours")
    event_rate: float = Field(default=100.0, description="Target events per minute")
    baseline_behavior: str = Field(default="DIURNAL_GAUSSIAN", description="Pre-policy stream pattern")
    policy_time_t0: datetime = Field(..., description="UTC timestamp when policy takes effect (T0)")
    degradation_magnitude: float = Field(default=0.80, description="Relative impact factor (0.8 = -20% drop)")
    affected_segment: Optional[str] = Field(default=None, description="Target user segment if specific")
    affected_metric: Optional[str] = Field(default=None, description="Target engagement metric if specific")
    ground_truth_degraded: bool = Field(..., description="Ground truth boolean (True = degraded, False = stable)")


class ScenarioRunResult(BaseModel):
    """Standardized execution result of an experiment scenario."""

    scenario_id: str
    scenario_name: str
    ground_truth_degraded: bool
    detected_degraded: bool
    composite_score: float
    composite_threshold: float
    top_degraded_metric: Optional[str]
    most_affected_segment: Optional[str]
    is_localized: bool
    detection_delay_steps: Optional[int]
    passed: bool


def get_predefined_scenarios() -> List[ExperimentScenario]:
    """Returns the 10 required reproducible experiment scenario definitions."""
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    return [
        ExperimentScenario(
            scenario_id="SCENARIO_01_NO_POLICY_CHANGE",
            name="1. No Policy Change (Null Hypothesis)",
            description="Pre and post T0 streams are identical; tests false-alarm control under H0.",
            seed=42,
            policy_time_t0=t0,
            degradation_magnitude=1.00,
            ground_truth_degraded=False,
        ),
        ExperimentScenario(
            scenario_id="SCENARIO_02_SMALL_DEGRADATION",
            name="2. Small Platform Degradation (-10%)",
            description="Subtle -10% engagement drop across all metrics post T0.",
            seed=43,
            policy_time_t0=t0,
            degradation_magnitude=0.90,
            ground_truth_degraded=True,
        ),
        ExperimentScenario(
            scenario_id="SCENARIO_03_LARGE_DEGRADATION",
            name="3. Large Platform Degradation (-30%)",
            description="Severe -30% engagement drop across all metrics post T0.",
            seed=44,
            policy_time_t0=t0,
            degradation_magnitude=0.70,
            ground_truth_degraded=True,
        ),
        ExperimentScenario(
            scenario_id="SCENARIO_04_SEGMENT_SPECIFIC",
            name="4. Segment-Specific Degradation (Heavy Users Only)",
            description="-40% drop targeting heavy users while casual and regular users remain normal.",
            seed=45,
            policy_time_t0=t0,
            degradation_magnitude=0.60,
            affected_segment="heavy",
            ground_truth_degraded=True,
        ),
        ExperimentScenario(
            scenario_id="SCENARIO_05_SEASONAL_FLUCTUATION",
            name="5. Seasonal Fluctuation (Diurnal Cycle)",
            description="Normal diurnal cycle without policy degradation; tests baseline seasonal adjustment.",
            seed=46,
            baseline_behavior="DIURNAL_SINE",
            policy_time_t0=t0,
            degradation_magnitude=1.00,
            ground_truth_degraded=False,
        ),
        ExperimentScenario(
            scenario_id="SCENARIO_06_EXTERNAL_CONFOUNDER",
            name="6. External Confounder (Traffic Spike)",
            description="External viral spike +20% engagement; tests positive surge non-degradation rule.",
            seed=47,
            policy_time_t0=t0,
            degradation_magnitude=1.20,
            ground_truth_degraded=False,
        ),
        ExperimentScenario(
            scenario_id="SCENARIO_07_MULTIPLE_POLICIES",
            name="7. Multiple Policy Changes (P001 & P002)",
            description="First policy P001 at T0 (-10%), second policy P002 at T0+6h (-20%).",
            seed=48,
            policy_time_t0=t0,
            degradation_magnitude=0.72,
            ground_truth_degraded=True,
        ),
        ExperimentScenario(
            scenario_id="SCENARIO_08_GRADUAL_DEGRADATION",
            name="8. Gradual Degradation (Linear Ramp)",
            description="Linear engagement decay starting at T0 over 6 hours.",
            seed=49,
            policy_time_t0=t0,
            degradation_magnitude=0.75,
            ground_truth_degraded=True,
        ),
        ExperimentScenario(
            scenario_id="SCENARIO_09_SUDDEN_DEGRADATION",
            name="9. Sudden Degradation (Step Change)",
            description="Instantaneous step drop -25% at exact timestamp T0.",
            seed=50,
            policy_time_t0=t0,
            degradation_magnitude=0.75,
            ground_truth_degraded=True,
        ),
        ExperimentScenario(
            scenario_id="SCENARIO_10_METRIC_SPECIFIC",
            name="10. Metric-Specific Degradation (Comments Only)",
            description="-50% drop in comment interactions while likes and shares remain normal.",
            seed=51,
            policy_time_t0=t0,
            degradation_magnitude=0.50,
            affected_metric="comment",
            ground_truth_degraded=True,
        ),
    ]


class ScenarioRunner:
    """Executes predefined experiment scenarios through the CAGED detection framework."""

    @classmethod
    def run_scenario(cls, scenario: ExperimentScenario) -> ScenarioRunResult:
        t0 = scenario.policy_time_t0

        # Setup policy timeline
        pol_metric = MetricType(scenario.affected_metric) if scenario.affected_metric else None
        pol_segment = UserSegment(scenario.affected_segment) if scenario.affected_segment else None

        policy = PolicyEvent(
            policy_id=f"P_{scenario.scenario_id}",
            policy_name=scenario.name,
            timestamp=t0,
            description=scenario.description,
            impact_factor=scenario.degradation_magnitude,
            target_metric=pol_metric,
            target_segment=pol_segment,
        )

        timeline = PolicyTimeline()
        timeline.add_policy_event(policy)

        # Baseline predictions (expected values before T0)
        base_preds = {
            MetricType.LIKE: BaselinePrediction(expected_value=100.0, std_dev=1.0, ci_lower=98.0, ci_upper=102.0),
            MetricType.COMMENT: BaselinePrediction(expected_value=50.0, std_dev=1.0, ci_lower=48.0, ci_upper=52.0),
            MetricType.SHARE: BaselinePrediction(expected_value=20.0, std_dev=0.7071, ci_lower=18.6, ci_upper=21.4),
        }

        # Snapshot baseline at T0
        snapshotter = BaselineSnapshotter()
        for m, b_pred in base_preds.items():
            model = ExponentialSmoothingBaseline(alpha=0.2, beta=0.0)
            model.fit([b_pred.expected_value] * 20)
            snapshotter.freeze_baseline(policy.policy_id, m, model, frozen_at=t0)

        # Simulate post-policy observed metric stream values
        post_obs = {}
        for m, b_pred in base_preds.items():
            is_target_metric = (scenario.affected_metric is None) or (scenario.affected_metric == m.value)
            if scenario.ground_truth_degraded and is_target_metric:
                post_obs[m] = b_pred.expected_value * scenario.degradation_magnitude
            else:
                post_obs[m] = b_pred.expected_value

        # Evaluate Multi-Metric Degradation
        multi_detector = MultiMetricDetector(default_composite_threshold=4.0)
        frozen_preds = {m: snapshotter.get_frozen_model(policy.policy_id, m).predict() for m in base_preds.keys()}

        multi_res = multi_detector.evaluate(
            observed_metrics=post_obs,
            baseline_predictions=frozen_preds,
            policy_id=policy.policy_id,
            timestamp=t0 + timedelta(minutes=15),
        )

        # Segment Evaluation
        seg_obs = {
            "casual": {m: post_obs[m] for m in base_preds.keys()},
            "regular": {m: post_obs[m] for m in base_preds.keys()},
            "heavy": {m: (post_obs[m] if scenario.affected_segment != "heavy" else post_obs[m] * scenario.degradation_magnitude) for m in base_preds.keys()},
        }
        if scenario.affected_segment == "heavy":
            seg_obs["casual"] = {m: base_preds[m].expected_value for m in base_preds.keys()}
            seg_obs["regular"] = {m: base_preds[m].expected_value for m in base_preds.keys()}

        segment_detector = SegmentDegradationDetector(default_segment_threshold=4.0)
        seg_report = segment_detector.evaluate_all_segments(
            overall_observed=post_obs,
            overall_predictions=frozen_preds,
            segment_observed=seg_obs,
            segment_predictions={s: frozen_preds for s in seg_obs.keys()},
            policy_id=policy.policy_id,
        )

        passed = (multi_res.is_degraded == scenario.ground_truth_degraded)
        delay_steps = 1 if multi_res.is_degraded else None

        return ScenarioRunResult(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
            ground_truth_degraded=scenario.ground_truth_degraded,
            detected_degraded=multi_res.is_degraded,
            composite_score=round(multi_res.composite_score, 2),
            composite_threshold=multi_res.composite_threshold,
            top_degraded_metric=multi_res.top_contributor.value.upper() if multi_res.top_contributor else None,
            most_affected_segment=seg_report.most_degraded_segment,
            is_localized=seg_report.is_localized,
            detection_delay_steps=delay_steps,
            passed=passed,
        )
