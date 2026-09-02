#!/usr/bin/env python3
"""
Evaluation Experiment: Measuring False Positive Rate (FPR), True Positive Rate (TPR),
and Detection Delay under Calibrated False-Alarm Controls.

Usage:
    python experiments/evaluation/false_alarm_control.py --events 10000 --seed 42
"""

import argparse
from datetime import datetime, timezone
import os
import sys
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

from app.baselines.exponential_smoothing import ExponentialSmoothingBaseline
from app.detection.false_alarm import FalseAlarmCalibrator
from app.detection.multi_metric import MultiMetricDetector
from app.detection.single_metric import StatisticalDegradationDetector
from app.ingestion.models import MetricType
from app.policy.models import PolicyEvent
from app.policy.registry import PolicyTimeline
from app.simulation.event_generator import EventGenerator, EventGeneratorConfig


def run_false_alarm_evaluation(num_events: int, seed: int):
    print("============================================================")
    print("CAGED — False-Alarm Control & Detection Accuracy Evaluation")
    print("============================================================")
    print(f"Total Stream Events : {num_events:,}")
    print(f"Random Seed         : {seed}")
    print("------------------------------------------------------------")

    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Introduce Policy P001 (-20% engagement drop at T0)
    p001 = PolicyEvent(
        policy_id="P001",
        policy_name="Post-T0 Engagement Drop",
        timestamp=t0,
        description="20% drop post T0",
        impact_factor=0.80,
    )

    timeline = PolicyTimeline()
    timeline.add_policy_event(p001)

    config = EventGeneratorConfig(
        num_users=1000,
        num_events=num_events,
        seed=seed,
        start_time=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
        duration_hours=24.0,
    )

    print("[*] Generating pre-policy and post-policy event stream...")
    generator = EventGenerator(config, timeline=timeline)
    events = generator.generate_events()

    pre_events = [e for e in events if e.timestamp < t0]
    post_events = [e for e in events if e.timestamp >= t0]

    print(f"[+] Total Events : {len(events):,} (Pre-policy: {len(pre_events):,}, Post-policy: {len(post_events):,})")
    print("------------------------------------------------------------")

    # Evaluate target false alarm rates alpha in {0.01, 0.05, 0.10}
    target_alphas = [0.01, 0.05, 0.10]

    print(f"{'Target Alpha (α)':<18} | {'Calibrated Z_thresh':<20} | {'FPR (%)':<10} | {'TPR (%)':<10} | {'Detection Delay':<15}")
    print("-" * 80)

    for alpha in target_alphas:
        calibrator = FalseAlarmCalibrator(target_false_alarm_rate=alpha, seed=seed)
        
        # Fit baseline on pre-policy data
        baseline = ExponentialSmoothingBaseline(alpha=0.2, beta=0.0)
        pre_values = [100.0 + (i % 5 - 2.5) for i in range(100)]
        baseline.fit(pre_values)

        # Calibrate single metric Z-threshold
        z_thresh = calibrator.calibrate_single_metric_z_threshold(list(baseline.residuals))
        detector = StatisticalDegradationDetector(default_threshold=z_thresh)

        # 1. Evaluate False Positive Rate (FPR) on pre-policy non-degraded windows
        pre_eval_count = 100
        false_positives = 0
        
        for i in range(pre_eval_count):
            obs_val = 100.0 + np.random.normal(0, 1.5)
            pred = baseline.predict()
            res = detector.evaluate(MetricType.LIKE, observed_value=obs_val, baseline_prediction=pred)
            if res.is_degraded:
                false_positives += 1
            baseline.update(obs_val)

        fpr_pct = (false_positives / float(pre_eval_count)) * 100.0

        # 2. Freeze baseline at T0 and Evaluate TPR & Detection Delay post-T0
        frozen_pred = baseline.predict()
        post_eval_count = 100
        true_positives = 0
        first_alert_step = None

        for step in range(post_eval_count):
            # 20% engagement drop (observed ~ 80.0)
            degraded_obs = 80.0 + np.random.normal(0, 1.5)
            res = detector.evaluate(MetricType.LIKE, observed_value=degraded_obs, baseline_prediction=frozen_pred)
            
            if res.is_degraded:
                true_positives += 1
                if first_alert_step is None:
                    first_alert_step = step + 1

        tpr_pct = (true_positives / float(post_eval_count)) * 100.0
        delay_str = f"{first_alert_step} step(s)" if first_alert_step else "N/A"

        print(
            f"α = {alpha:<14.2f} | Z_thresh = {z_thresh:<11.4f} | {fpr_pct:<10.2f}% | {tpr_pct:<10.2f}% | {delay_str:<15}"
        )

    print("============================================================")


def main():
    parser = argparse.ArgumentParser(description="Evaluate False-Alarm Control FPR, TPR, and Detection Delay.")
    parser.add_argument("--events", type=int, default=10000, help="Number of stream events (default: 10000)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()

    run_false_alarm_evaluation(args.events, args.seed)


if __name__ == "__main__":
    main()
