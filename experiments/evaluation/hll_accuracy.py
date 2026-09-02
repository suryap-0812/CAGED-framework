#!/usr/bin/env python3
"""
Evaluation Experiment: HyperLogLog Unique User Cardinality Estimation vs Exact Set.

Usage:
    python experiments/evaluation/hll_accuracy.py --cardinality 50000
"""

import argparse
import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

from app.preprocessing.privacy import pseudonymize_user_id
from app.sketches.hyperloglog import HyperLogLog


def run_hll_evaluation(target_cardinality: int, seed: int):
    print("============================================================")
    print("CAGED — HyperLogLog Unique-User Cardinality Evaluation")
    print("============================================================")
    print(f"Target Unique Users : {target_cardinality:,}")
    print(f"Random Seed         : {seed}")
    print("------------------------------------------------------------")

    np_rng = np.random.default_rng(seed)

    # Pre-generate unique synthetic user hashes with duplicates (repeats simulating session activity)
    raw_user_ids = [f"user_{i}" for i in range(target_cardinality)]
    user_hashes = [pseudonymize_user_id(uid) for uid in raw_user_ids]
    
    # Create stream with ~3x repeat interactions per user
    stream = np_rng.choice(user_hashes, size=target_cardinality * 3).tolist()

    # 1. Exact Set Cardinality
    print("[*] Computing exact unique user set...")
    t0 = time.monotonic()
    exact_set = set(stream)
    exact_time = time.monotonic() - t0
    exact_count = len(exact_set)

    # Approximate memory of Python set containing 64-char strings
    set_memory_bytes = sys.getsizeof(exact_set) + sum(sys.getsizeof(s) for s in exact_set)
    set_memory_kb = set_memory_bytes / 1024.0

    print(f"[+] Exact unique count : {exact_count:,}")
    print(f"    Set Computation    : {exact_time:.4f} seconds")
    print(f"    Set Memory Usage   : {set_memory_kb:,.2f} KB ({set_memory_bytes:,} bytes)")
    print("------------------------------------------------------------")

    # 2. Evaluate HyperLogLog across multiple precision levels (p=10, p=12, p=14)
    precisions = [10, 12, 14]

    print(f"{'Precision (p)':<15} | {'Registers (m)':<15} | {'Memory (KB)':<12} | {'Estimated':<12} | {'Rel Error (%)':<14} | {'Exp Error (%)':<14}")
    print("-" * 92)

    for p in precisions:
        hll = HyperLogLog(p=p, seed=seed)
        t_start = time.monotonic()
        for u_hash in stream:
            hll.add(u_hash)
        est = hll.estimate()

        rel_err = abs(est - exact_count) / float(exact_count) * 100.0
        exp_err = hll.expected_relative_error() * 100.0
        hll_memory_kb = hll.memory_bytes() / 1024.0

        print(
            f"p={p:<13} | {hll.m:<15,} | {hll_memory_kb:<12.2f} | {est:<12,.0f} | {rel_err:<14.2f}% | {exp_err:<14.2f}%"
        )

    print("============================================================")
    print("WHY HYPERLOGLOG IS USED IN CAGED:")
    print("1. Memory Savings : Exact set storage grows linearly with user count (e.g. 50,000 users = ~8 MB).")
    print("                    HyperLogLog uses constant memory (16 KB for p=14) regardless of stream volume.")
    print("2. Mergeability   : HyperLogLog sketches from parallel window streams can be merged cleanly")
    print("                    using entry-wise max, enabling real-time distributed tracking.")
    print("============================================================")


def main():
    parser = argparse.ArgumentParser(description="Evaluate HyperLogLog cardinality estimation accuracy.")
    parser.add_argument("--cardinality", type=int, default=50000, help="Target unique user count (default: 50000)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()

    run_hll_evaluation(args.cardinality, args.seed)


if __name__ == "__main__":
    main()
