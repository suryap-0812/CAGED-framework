"""
Phase 6 Full Evaluation Benchmark Execution Script.
Executes 500 independent evaluation runs (100 runs per scenario across 5 scenarios).
Exports machine-readable JSON & CSV datasets to backend/benchmark_results.json and backend/benchmark_results.csv.
"""

import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.evaluation.benchmark_runner import CAGEDBenchmarkRunner


def main():
    print("=" * 70)
    print("Starting CAGED Phase 6 Empirical Evaluation Benchmark (K=500 Runs)...")
    print("=" * 70)

    runner = CAGEDBenchmarkRunner(base_seed=100000)
    records = runner.run_benchmark(runs_per_scenario=100)

    json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "benchmark_results.json"))
    csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "benchmark_results.csv"))

    runner.export_results(json_path, csv_path)

    print("-" * 70)
    print(f"Benchmark completed successfully! Executed {len(records)} total evaluation runs.")
    print(f"Exported JSON dataset to: {json_path}")
    print(f"Exported CSV dataset to:  {csv_path}")
    print("-" * 70)

    summary = runner.generate_summary_statistics()
    for scen_id, s in summary.items():
        print(f"\nScenario: {s['scenario_name']} ({scen_id})")
        print(f"  CAGED Rate ({s['caged_detection']['rate_type']}): {s['caged_detection']['empirical_rate']*100:.1f}% (95% CI: [{s['caged_detection']['ci_95_lower']*100:.1f}%, {s['caged_detection']['ci_95_upper']*100:.1f}%])")
        print(f"  CAGED Latency (min / median / max): {s['caged_latency_minutes']['min']}m / {s['caged_latency_minutes']['median']}m / {s['caged_latency_minutes']['max']}m")
        print(f"  ML Counterfactual (R2 / RMSE / MAE): {s['ml_counterfactual']['mean_r2']} / {s['ml_counterfactual']['mean_rmse']} / {s['ml_counterfactual']['mean_mae']}")
        print(f"  DiD Estimator Mean Tau Hat: {s['did_estimator']['mean_tau_hat']:.6f} (True Tau: {s['did_estimator']['mean_tau_true']:.6f})")
        print(f"  DiD Bias: {s['did_estimator']['mean_bias']:.6f} | RMSE: {s['did_estimator']['rmse']:.6f}")
        print(f"  DiD 95% CI Coverage: {s['did_estimator']['ci_95_coverage']['empirical_rate']*100:.1f}% (95% CI: [{s['did_estimator']['ci_95_coverage']['ci_95_lower']*100:.1f}%, {s['did_estimator']['ci_95_coverage']['ci_95_upper']*100:.1f}%])")
        print(f"  SUTVA Control Delta Mean (SD): {s['no_interference_control_cohort']['mean_control_delta']:.6f} ({s['no_interference_control_cohort']['sd_control_delta']:.6f})")


if __name__ == "__main__":
    main()
