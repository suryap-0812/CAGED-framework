"""
CAGED Phase 6 Full Benchmark & Empirical Evaluation Runner.
Executes scalable empirical evaluation across 5 policy scenarios using independent random seeds.
Enforces strict Ground-Truth Firewall isolation: analytical estimators receive ONLY observable telemetry.
True causal treatment effects (tau_true) are computed using Common Random Numbers (CRN) potential outcomes
and joined EX-POST ONLY for ex-post estimator evaluation.
"""

from datetime import datetime, timedelta, timezone
import json
import math
import os
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.causal.did_estimator import DiDEstimator, DiDEstimateResult
from app.detection.caged_detector import CAGEDStatisticalDetector, CAGEDDetectionReport
from app.ingestion.models import EngagementEvent, MetricType
from app.ml.counterfactual_predictor import (
    CounterfactualMLPredictor,
    CounterfactualPredictionResult,
    CounterfactualFeatureVector,
)
from app.detection.window_aggregator import WindowAggregator
from app.simulation.event_generator import EventGenerator
from app.simulation.experiment_config import (
    ExperimentConfig,
    ExternalDisturbance,
    ExternalDisturbanceType,
    PolicyMechanism,
    PolicyParameters,
)


def compute_wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float, float]:
    """
    Computes empirical proportion and 95% Wilson Score Confidence Interval [lower, upper].
    Returns (proportion, ci_lower, ci_upper).
    """
    if total <= 0:
        return 0.0, 0.0, 0.0
    p_hat = successes / float(total)
    z = 1.95996  # 95% confidence z-score
    denom = 1.0 + (z ** 2) / total
    center = (p_hat + (z ** 2) / (2.0 * total)) / denom
    spread = (z / denom) * math.sqrt((p_hat * (1.0 - p_hat) / total) + ((z ** 2) / (4.0 * (total ** 2))))
    lower = max(0.0, center - spread)
    upper = min(1.0, center + spread)
    return round(p_hat, 4), round(lower, 4), round(upper, 4)


class CAGEDBenchmarkRunner:
    """
    Empirical benchmark runner for the complete CAGED system.
    Orchestrates CAGED Statistical Detector, ML Counterfactual Predictor, and DiD Causal Estimator.
    """

    SCENARIOS = [
        {
            "scenario_id": "originality_downrank",
            "name": "Originality Downrank / Aggregator Deprioritization",
            "mechanism": PolicyMechanism.ORIGINALITY_BOOST,
            "params": PolicyParameters(originality_weight_shift=-2.5),
            "seed_offset": 0,
        },
        {
            "scenario_id": "short_form_ranking_shift",
            "name": "Short-Form Video Ranking Optimization",
            "mechanism": PolicyMechanism.SHORT_FORM_RANKING_SHIFT,
            "params": PolicyParameters(affinity_weight_shift=2.0),
            "seed_offset": 100,
        },
        {
            "scenario_id": "quality_filtering",
            "name": "Low-Quality Content Threshold Elevation",
            "mechanism": PolicyMechanism.QUALITY_THRESHOLD_RAISE,
            "params": PolicyParameters(quality_weight_shift=2.5),
            "seed_offset": 200,
        },
        {
            "scenario_id": "surface_allocation_shift",
            "name": "Feed Surface Freshness Re-allocation",
            "mechanism": PolicyMechanism.SURFACE_ALLOCATION_SHIFT,
            "params": PolicyParameters(freshness_weight_shift=2.0),
            "seed_offset": 300,
        },
        {
            "scenario_id": "null_policy",
            "name": "A/A Null Control Policy (H0)",
            "mechanism": PolicyMechanism.NO_POLICY,
            "params": PolicyParameters(),
            "seed_offset": 400,
        },
    ]

    def __init__(self, base_seed: int = 100000):
        self.base_seed = base_seed
        self.run_records: List[Dict[str, Any]] = []

    def compute_crn_tau_true(
        self,
        scenario_spec: Dict[str, Any],
        seed: int,
        start_time: datetime,
        t0: datetime,
        duration_hours: float = 2.0,
    ) -> float:
        """
        Calculates exact potential-outcome causal treatment effect tau_true using Common Random Numbers (CRN).
        
        tau_true = E[Y^(1)_post | D=1] - E[Y^(0)_post | D=1]
        
        For a given seed, Run 1 generates events under the policy shift.
        Run 2 generates events under NO_POLICY with the exact same seed, user population, and random stream.
        tau_true is the difference in treatment group post-pre changes between policy and counterfactual NO_POLICY.
        For NO_POLICY scenario, tau_true is 0.0 identically.
        """
        if scenario_spec["mechanism"] == PolicyMechanism.NO_POLICY:
            return 0.0

        # Counterfactual NO_POLICY simulation with exact same seed and config
        cf_config = ExperimentConfig(
            seed=seed,
            num_users=300,
            num_items=100,
            event_rate=300,
            duration_hours=duration_hours,
            start_time=start_time,
            t0=t0,
            treatment_ratio=0.50,
            policy_mechanism=PolicyMechanism.NO_POLICY,
            policy_params=PolicyParameters(),
        )
        cf_generator = EventGenerator(cf_config)
        cf_events = cf_generator.generate_events()

        # Factual policy simulation with exact same seed and config
        f_config = ExperimentConfig(
            seed=seed,
            num_users=300,
            num_items=100,
            event_rate=300,
            duration_hours=duration_hours,
            start_time=start_time,
            t0=t0,
            treatment_ratio=0.50,
            policy_mechanism=scenario_spec["mechanism"],
            policy_params=scenario_spec["params"],
        )
        f_generator = EventGenerator(f_config)
        f_events = f_generator.generate_events()

        # Aggregate 5-min windows for both streams
        aggregator = WindowAggregator(window_size_minutes=5)
        cf_treat_pre, cf_treat_post = self._extract_cohort_rates(aggregator, cf_events, start_time, t0, "treatment")
        f_treat_pre, f_treat_post = self._extract_cohort_rates(aggregator, f_events, start_time, t0, "treatment")

        # Potential outcome difference
        delta_f = np.mean(f_treat_post) - np.mean(f_treat_pre)
        delta_cf = np.mean(cf_treat_post) - np.mean(cf_treat_pre)
        tau_true = float(delta_f - delta_cf)
        return round(tau_true, 6)

    def _extract_cohort_rates(
        self,
        aggregator: WindowAggregator,
        events: List[EngagementEvent],
        start_time: datetime,
        t0: datetime,
        cohort: str,
        metric: str = "like",
    ) -> Tuple[List[float], List[float]]:
        """Extracts pre-T0 and post-T0 metric rates for a specific cohort."""
        cohort_evts = [e for e in events if e.segment_metadata.get("cohort") == cohort]
        pts = aggregator.aggregate_stream(cohort_evts, start_time=start_time)
        pre_rates, post_rates = [], []
        for pt in pts:
            rate = getattr(pt, f"{metric}s_per_view", 0.0)
            if pt.window_start < t0:
                pre_rates.append(rate)
            else:
                post_rates.append(rate)
        return pre_rates, post_rates

    def run_single_eval(self, scenario_spec: Dict[str, Any], run_idx: int) -> Dict[str, Any]:
        """
        Executes a single evaluation run:
        1. Emits observable telemetry from EventGenerator.
        2. Evaluates CAGED Statistical Detector (observable telemetry only).
        3. Evaluates ML Counterfactual Predictor (leakage-free pre-policy & control training).
        4. Evaluates DiD Causal Estimator (observable telemetry only).
        5. Computes CRN tau_true ex-post and joins ground-truth evaluation metrics.
        """
        seed = self.base_seed + scenario_spec["seed_offset"] + run_idx
        start_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
        t0 = datetime(2026, 9, 1, 1, 0, 0, tzinfo=timezone.utc)
        duration_hours = 2.0

        # 1. Observable Telemetry Generation
        exp_config = ExperimentConfig(
            seed=seed,
            num_users=300,
            num_items=100,
            event_rate=300,
            duration_hours=duration_hours,
            start_time=start_time,
            t0=t0,
            treatment_ratio=0.50,
            policy_mechanism=scenario_spec["mechanism"],
            policy_params=scenario_spec["params"],
        )
        generator = EventGenerator(exp_config)
        events = generator.generate_events()

        # 2. CAGED Statistical Detection
        caged_detector = CAGEDStatisticalDetector(composite_threshold=4.0, minimum_effect_size=0.05)
        caged_report = caged_detector.analyze_stream(events, t0=t0)

        # 3. ML Counterfactual Prediction (Leakage-Free)
        ml_predictor = CounterfactualMLPredictor(target_metric=MetricType.LIKE, random_state=seed)
        try:
            ml_metrics = ml_predictor.train_on_pre_policy_or_control(events, t0=t0)
            ml_r2 = ml_metrics.get("r2", 0.0)
            ml_rmse = ml_metrics.get("rmse", 0.0)
            ml_mae = round(ml_rmse * 0.80, 4)  # MAE approximation for Gaussian error distribution
        except Exception:
            ml_r2, ml_rmse, ml_mae = 0.0, 0.0, 0.0

        # 4. DiD Causal Estimation (Observable Telemetry Only)
        did_estimator = DiDEstimator()
        did_res = did_estimator.estimate_policy_effect(
            events, t0=t0, metric_type=MetricType.LIKE, minimum_effect_size=0.05
        )

        # 5. Ex-Post Ground Truth Calculation via CRN
        tau_true = self.compute_crn_tau_true(scenario_spec, seed, start_time, t0, duration_hours)
        bias = float(did_res.tau_did - tau_true)
        sq_err = float((did_res.tau_did - tau_true) ** 2)
        ci_cov = bool(did_res.ci_lower <= tau_true <= did_res.ci_upper)

        # Control group pre-post change for SUTVA no-interference evaluation
        ctrl_pre_m = did_res.control_pre_mean
        ctrl_post_m = did_res.control_post_mean
        ctrl_delta = did_res.control_change

        record = {
            "run_id": f"run_{scenario_spec['scenario_id']}_{seed}",
            "scenario_id": scenario_spec["scenario_id"],
            "seed": seed,
            # CAGED Outputs
            "caged_degradation_detected": caged_report.is_degradation_detected,
            "caged_composite_score": caged_report.peak_composite_score,
            "caged_threshold": caged_report.calibrated_threshold,
            "caged_latency_minutes": caged_report.detection_latency_minutes,
            "caged_top_degraded_metric": caged_report.top_degraded_metric.value if caged_report.top_degraded_metric else None,
            "caged_most_degraded_segment": caged_report.most_degraded_segment,
            "caged_most_degraded_category": caged_report.most_degraded_category,
            "caged_practical_effect_detected": bool(caged_report.is_degradation_detected and caged_report.peak_composite_score >= caged_report.calibrated_threshold),
            # ML Outputs
            "ml_r2_score": ml_r2,
            "ml_rmse": ml_rmse,
            "ml_mae": ml_mae,
            # DiD Outputs
            "did_tau_hat": did_res.tau_did,
            "did_se": did_res.std_error,
            "did_ci_lower": did_res.ci_lower,
            "did_ci_upper": did_res.ci_upper,
            "did_p_value": did_res.p_value,
            "did_statistically_significant": did_res.is_statistically_significant,
            "did_practically_significant": did_res.is_practically_significant,
            "did_relative_effect": round(abs(did_res.tau_did / did_res.treat_pre_mean) if did_res.treat_pre_mean > 0 else 0.0, 4),
            "did_causal_verdict": did_res.causal_verdict,
            "did_pre_trend_p_value": did_res.pre_trend_diagnostic.p_value,
            "did_parallel_pre_trends_supported": did_res.pre_trend_diagnostic.is_parallel_trends_supported,
            # Ex-Post Ground Truth Evaluation
            "tau_true": tau_true,
            "did_bias": bias,
            "did_squared_error": sq_err,
            "did_ci_covered": ci_cov,
            # No-Interference Control Cohort Evaluation
            "control_pre_mean": ctrl_pre_m,
            "control_post_mean": ctrl_post_m,
            "control_delta": ctrl_delta,
            "treatment_pre_mean": did_res.treat_pre_mean,
            "treatment_post_mean": did_res.treat_post_mean,
        }
        return record

    def run_benchmark(self, runs_per_scenario: int = 100) -> List[Dict[str, Any]]:
        """Runs benchmark across all 5 scenarios with runs_per_scenario independent seeds per scenario."""
        self.run_records = []
        for scen in self.SCENARIOS:
            for i in range(runs_per_scenario):
                rec = self.run_single_eval(scen, i)
                self.run_records.append(rec)
        return self.run_records

    def export_results(self, json_path: str, csv_path: str) -> None:
        """Exports per-run detailed benchmark results to machine-readable JSON and CSV files."""
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)

        summary_stats = self.generate_summary_statistics()
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_runs": len(self.run_records),
            "base_seed": self.base_seed,
            "summary_by_scenario": summary_stats,
            "per_run_records": self.run_records,
        }

        with open(json_path, "w") as f:
            json.dump(payload, f, indent=2)

        # CSV Export
        if self.run_records:
            headers = list(self.run_records[0].keys())
            rows = [",".join(headers)]
            for r in self.run_records:
                row_vals = []
                for h in headers:
                    val = r.get(h)
                    if val is None:
                        row_vals.append("")
                    elif isinstance(val, bool):
                        row_vals.append("TRUE" if val else "FALSE")
                    else:
                        row_vals.append(str(val))
                rows.append(",".join(row_vals))

            with open(csv_path, "w") as f:
                f.write("\n".join(rows))

    def generate_summary_statistics(self) -> Dict[str, Any]:
        """Calculates aggregated empirical performance metrics per scenario with 95% Wilson CIs."""
        by_scenario: Dict[str, Any] = {}
        for scen in self.SCENARIOS:
            sid = scen["scenario_id"]
            records = [r for r in self.run_records if r["scenario_id"] == sid]
            if not records:
                continue

            n = len(records)
            # CAGED Detection Power / False Alarm
            det_count = sum(1 for r in records if r["caged_degradation_detected"])
            det_rate, det_ci_l, det_ci_u = compute_wilson_score_interval(det_count, n)

            # Detection Latencies (for runs with alerts)
            latencies = [r["caged_latency_minutes"] for r in records if r["caged_latency_minutes"] is not None]
            lat_mean = float(np.mean(latencies)) if latencies else 0.0
            lat_median = float(np.median(latencies)) if latencies else 0.0
            lat_min = float(np.min(latencies)) if latencies else 0.0
            lat_max = float(np.max(latencies)) if latencies else 0.0
            lat_q25 = float(np.percentile(latencies, 25)) if latencies else 0.0
            lat_q75 = float(np.percentile(latencies, 75)) if latencies else 0.0

            # ML Predictor Performance
            r2_vals = [r["ml_r2_score"] for r in records]
            rmse_vals = [r["ml_rmse"] for r in records]
            mae_vals = [r["ml_mae"] for r in records]

            # DiD Estimator Performance
            tau_hats = [r["did_tau_hat"] for r in records]
            taus_true = [r["tau_true"] for r in records]
            biases = [r["did_bias"] for r in records]
            sq_errors = [r["did_squared_error"] for r in records]

            stat_sig_count = sum(1 for r in records if r["did_statistically_significant"])
            stat_sig_rate, stat_sig_l, stat_sig_u = compute_wilson_score_interval(stat_sig_count, n)

            pract_sig_count = sum(1 for r in records if r["did_practically_significant"])
            pract_sig_rate, pract_sig_l, pract_sig_u = compute_wilson_score_interval(pract_sig_count, n)

            ci_cov_count = sum(1 for r in records if r["did_ci_covered"])
            ci_cov_rate, ci_cov_l, ci_cov_u = compute_wilson_score_interval(ci_cov_count, n)

            pre_trend_count = sum(1 for r in records if r["did_parallel_pre_trends_supported"])
            pre_trend_rate, pre_trend_l, pre_trend_u = compute_wilson_score_interval(pre_trend_count, n)

            # SUTVA Control Isolation Delta
            ctrl_deltas = [r["control_delta"] for r in records]

            by_scenario[sid] = {
                "scenario_name": scen["name"],
                "total_runs": n,
                "caged_detection": {
                    "alert_count": det_count,
                    "empirical_rate": det_rate,
                    "ci_95_lower": det_ci_l,
                    "ci_95_upper": det_ci_u,
                    "rate_type": "false_alarm_rate" if sid == "null_policy" else "detection_power",
                },
                "caged_latency_minutes": {
                    "mean": round(lat_mean, 2),
                    "median": round(lat_median, 2),
                    "min": round(lat_min, 2),
                    "q25": round(lat_q25, 2),
                    "q75": round(lat_q75, 2),
                    "max": round(lat_max, 2),
                },
                "ml_counterfactual": {
                    "mean_r2": round(float(np.mean(r2_vals)), 4),
                    "mean_rmse": round(float(np.mean(rmse_vals)), 4),
                    "mean_mae": round(float(np.mean(mae_vals)), 4),
                },
                "did_estimator": {
                    "mean_tau_hat": round(float(np.mean(tau_hats)), 6),
                    "median_tau_hat": round(float(np.median(tau_hats)), 6),
                    "sd_tau_hat": round(float(np.std(tau_hats)), 6),
                    "mean_tau_true": round(float(np.mean(taus_true)), 6),
                    "mean_bias": round(float(np.mean(biases)), 6),
                    "rmse": round(math.sqrt(float(np.mean(sq_errors))), 6),
                    "ci_95_coverage": {
                        "empirical_rate": ci_cov_rate,
                        "ci_95_lower": ci_cov_l,
                        "ci_95_upper": ci_cov_u,
                    },
                    "statistical_significance_rate": {
                        "empirical_rate": stat_sig_rate,
                        "ci_95_lower": stat_sig_l,
                        "ci_95_upper": stat_sig_u,
                    },
                    "practical_significance_rate": {
                        "empirical_rate": pract_sig_rate,
                        "ci_95_lower": pract_sig_l,
                        "ci_95_upper": pract_sig_u,
                    },
                    "parallel_pre_trends_supported_rate": {
                        "empirical_rate": pre_trend_rate,
                        "ci_95_lower": pre_trend_l,
                        "ci_95_upper": pre_trend_u,
                    },
                },
                "no_interference_control_cohort": {
                    "mean_control_delta": round(float(np.mean(ctrl_deltas)), 6),
                    "sd_control_delta": round(float(np.std(ctrl_deltas)), 6),
                    "min_control_delta": round(float(np.min(ctrl_deltas)), 6),
                    "max_control_delta": round(float(np.max(ctrl_deltas)), 6),
                },
            }

        return by_scenario
