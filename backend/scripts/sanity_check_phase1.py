"""
Phase 1 Behavioral Sanity Check Script.
Runs a deterministic small-scale simulation comparing Treatment vs Control cohorts
under a realistic recommendation policy shift (e.g. ORIGINALITY_BOOST / QUALITY_THRESHOLD_RAISE).
"""

from datetime import datetime, timezone
import json
import numpy as np

from app.ingestion.models import MetricType
from app.simulation.event_generator import EventGenerator
from app.simulation.experiment_config import (
    ExperimentConfig,
    PolicyMechanism,
    PolicyParameters,
)


def run_sanity_check():
    # 1. Setup Config: 24h simulation, T0 at hour 12, seed 42
    start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    config = ExperimentConfig(
        seed=42,
        num_users=1000,
        num_items=500,
        event_rate=500,
        duration_hours=24.0,
        start_time=start_time,
        t0=t0,
        treatment_ratio=0.50,
        policy_mechanism=PolicyMechanism.ORIGINALITY_BOOST,
        policy_params=PolicyParameters(originality_weight_shift=2.5),
    )

    generator = EventGenerator(config)
    events = generator.generate_events()

    # 2. Separate events by Cohort (Treatment vs Control) and Timing (Pre-T0 vs Post-T0)
    pre_events = [e for e in events if e.timestamp < t0]
    post_events = [e for e in events if e.timestamp >= t0]

    def aggregate_metrics(event_list):
        treat_evts = [e for e in event_list if e.segment_metadata.get("cohort") == "treatment"]
        ctrl_evts = [e for e in event_list if e.segment_metadata.get("cohort") == "control"]

        def compute_cohort_stats(evts):
            views = sum(1 for e in evts if e.metric_type == MetricType.VIEW)
            likes = sum(1 for e in evts if e.metric_type == MetricType.LIKE)
            comments = sum(1 for e in evts if e.metric_type == MetricType.COMMENT)
            shares = sum(1 for e in evts if e.metric_type == MetricType.SHARE)
            clicks = sum(1 for e in evts if e.metric_type == MetricType.CLICK)
            sessions = [e.value for e in evts if e.metric_type == MetricType.SESSION_DURATION]
            avg_session = float(np.mean(sessions)) if sessions else 0.0

            return {
                "impressions_views": views,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "clicks": clicks,
                "avg_session_duration_sec": round(avg_session, 2),
                "total_events": len(evts),
            }

        return {
            "treatment": compute_cohort_stats(treat_evts),
            "control": compute_cohort_stats(ctrl_evts),
        }

    pre_stats = aggregate_metrics(pre_events)
    post_stats = aggregate_metrics(post_events)

    report = {
        "scenario": config.policy_mechanism.value,
        "seed": config.seed,
        "total_generated_events": len(events),
        "pre_policy_window_h0_h12": pre_stats,
        "post_policy_window_h12_h24": post_stats,
    }

    print("=================== CAGED PHASE 1 BEHAVIORAL SANITY CHECK ===================")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    run_sanity_check()
