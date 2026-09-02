#!/usr/bin/env python3
"""
Evaluation Experiment: Comparing Count-Min Sketch Accuracy & Memory vs Exact Counting.

Usage:
    python experiments/evaluation/sketch_accuracy.py --items 100000 --unique 5000
"""

import argparse
import sys
import os
import time
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

from app.sketches.count_min_sketch import CountMinSketch


def run_sketch_evaluation(total_items: int, unique_keys: int, seed: int):
    print("============================================================")
    print("CAGED — Count-Min Sketch Accuracy & Memory Evaluation")
    print("============================================================")
    print(f"Total Stream Items : {total_items:,}")
    print(f"Unique Item Keys   : {unique_keys:,}")
    print(f"Random Seed        : {seed}")
    print("------------------------------------------------------------")

    np_rng = np.random.default_rng(seed)
    
    # Generate Zipfian / power-law distributed item keys simulating realistic social media heavy hitters
    zipf_samples = np_rng.zipf(a=1.5, size=total_items)
    items = [f"item_{val % unique_keys:06d}" for val in zipf_samples]

    # 1. Exact Dictionary Counting
    print("[*] Computing exact frequency counts using Python dictionary...")
    t0 = time.monotonic()
    exact_counts = {}
    for item in items:
        exact_counts[item] = exact_counts.get(item, 0) + 1
    dict_time = time.monotonic() - t0

    # Calculate exact dict memory (approximate sys.getsizeof + keys/vals)
    dict_bytes = sys.getsizeof(exact_counts) + sum(sys.getsizeof(k) + sys.getsizeof(v) for k, v in exact_counts.items())

    print(f"[+] Exact counting complete in {dict_time:.4f}s. Unique keys: {len(exact_counts):,}")
    print(f"    Dictionary Memory: {dict_bytes / 1024:.2f} KB ({dict_bytes:,} bytes)")
    print("------------------------------------------------------------")

    # 2. Benchmark multiple Count-Min Sketch configurations
    sketch_configs = [
        {"name": "Compact (w=100, d=3)", "w": 100, "d": 3},
        {"name": "Balanced (w=500, d=5)", "w": 500, "d": 5},
        {"name": "High Precision (w=2000, d=5)", "w": 2000, "d": 5},
    ]

    print(f"{'Configuration':<30} | {'Memory (KB)':<11} | {'MAE':<8} | {'Max Abs Err':<11} | {'MRE (%)':<8}")
    print("-" * 80)

    for cfg in sketch_configs:
        cms = CountMinSketch(width=cfg["w"], depth=cfg["d"], seed=seed)
        
        # Populate CMS
        for item in items:
            cms.update(item, 1.0)
            
        cms_memory_kb = cms.memory_bytes() / 1024.0

        # Measure error metrics against exact counts
        abs_errors = []
        rel_errors = []

        for item, exact_freq in exact_counts.items():
            est_freq = cms.estimate(item)
            abs_err = est_freq - exact_freq  # CMS never underestimates, so est >= exact
            rel_err = abs_err / float(exact_freq) if exact_freq > 0 else 0.0

            abs_errors.append(abs_err)
            rel_errors.append(rel_err)

        mae = np.mean(abs_errors)
        max_abs_err = np.max(abs_errors)
        mre_pct = np.mean(rel_errors) * 100.0

        print(
            f"{cfg['name']:<30} | {cms_memory_kb:<11.2f} | {mae:<8.2f} | {max_abs_err:<11.0f} | {mre_pct:<8.2f}%"
        )

    print("============================================================")


def main():
    parser = argparse.ArgumentParser(description="Evaluate Count-Min Sketch accuracy and memory footprint.")
    parser.add_argument("--items", type=int, default=100000, help="Total stream items (default: 100000)")
    parser.add_argument("--unique", type=int, default=5000, help="Number of unique keys (default: 5000)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()

    run_sketch_evaluation(args.items, args.unique, args.seed)


if __name__ == "__main__":
    main()
