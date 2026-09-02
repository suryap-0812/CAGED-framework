#!/usr/bin/env python3
"""
Benchmark Script for Measuring Stream Ingestion Pipeline Throughput.

Usage:
    python scripts/benchmark_ingestion.py --events 50000 --batch-size 500
"""

import argparse
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.ingestion.pipeline import IngestionPipeline
from app.simulation.event_generator import EventGenerator, EventGeneratorConfig


async def run_benchmark(num_events: int, num_users: int, batch_size: int):
    print("============================================================")
    print("CAGED — Stream Ingestion Benchmark")
    print("============================================================")
    print(f"Target Events  : {num_events:,}")
    print(f"Target Users   : {num_users:,}")
    print(f"Batch Size     : {batch_size:,}")
    print("------------------------------------------------------------")

    # Step 1: Pre-generate events for benchmark
    print("[*] Pre-generating synthetic event stream...")
    gen_start = time.monotonic()
    config = EventGeneratorConfig(num_users=num_users, num_events=num_events, seed=42)
    generator = EventGenerator(config)
    events = generator.generate_events()
    gen_time = time.monotonic() - gen_start
    print(f"[+] Generated {len(events):,} events in {gen_time:.3f}s ({len(events)/gen_time:,.0f} gen-events/sec).")

    # Step 2: Initialize Pipeline
    pipeline = IngestionPipeline(capacity=50000, batch_size=batch_size, batch_timeout_sec=0.1)
    
    # Track consumed batches
    processed_count = 0

    async def benchmark_batch_handler(batch):
        nonlocal processed_count
        processed_count += len(batch)

    pipeline.register_batch_handler(benchmark_batch_handler)

    # Step 3: Run Producer and Consumer concurrently
    print("[*] Executing concurrent stream ingestion benchmark...")
    await pipeline.start_consumer_loop()

    bench_start = time.monotonic()
    # Produce events in chunks
    chunk_size = 1000
    for i in range(0, len(events), chunk_size):
        chunk = events[i : i + chunk_size]
        await pipeline.produce_batch(chunk)

    # Stop pipeline and wait for drain
    await pipeline.stop()
    bench_duration = time.monotonic() - bench_start

    metrics = pipeline.get_metrics()

    print("------------------------------------------------------------")
    print("BENCHMARK RESULTS:")
    print(f"Total Produced : {metrics.total_produced:,}")
    print(f"Total Consumed : {metrics.total_consumed:,}")
    print(f"Total Rejected : {metrics.total_rejected:,}")
    print(f"Elapsed Time   : {metrics.elapsed_time_sec:.4f} seconds")
    print(f"Throughput     : {metrics.throughput_events_per_sec:,.2f} events/sec")
    print("============================================================")


def main():
    parser = argparse.ArgumentParser(description="Benchmark CAGED Ingestion Pipeline throughput.")
    parser.add_argument("--events", type=int, default=50000, help="Number of events to ingest (default: 50000)")
    parser.add_argument("--users", type=int, default=1000, help="Number of synthetic users (default: 1000)")
    parser.add_argument("--batch-size", type=int, default=500, help="Consumer batch size (default: 500)")
    args = parser.parse_args()

    asyncio.run(run_benchmark(args.events, args.users, args.batch_size))


if __name__ == "__main__":
    main()
