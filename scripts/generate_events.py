#!/usr/bin/env python3
"""
CLI Script for Generating Reproducible Synthetic Social Platform Event Streams.

Usage Example:
    python scripts/generate_events.py --users 1000 --events 10000 --seed 42 --output data/generated/synthetic_events.json
"""

import argparse
from datetime import datetime, timezone
import json
import os
import sys

# Ensure backend package is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.simulation.event_generator import EventGenerator, EventGeneratorConfig
from app.simulation.user_profile import UserSegment


def main():
    parser = argparse.ArgumentParser(
        description="Generate privacy-safe synthetic social-platform engagement event streams."
    )
    parser.add_argument(
        "--users", type=int, default=1000, help="Number of synthetic users to generate (default: 1000)"
    )
    parser.add_argument(
        "--events", type=int, default=10000, help="Total number of events to generate (default: 10000)"
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)"
    )
    parser.add_argument(
        "--duration", type=float, default=24.0, help="Time span duration in hours (default: 24.0)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/generated/synthetic_events.json",
        help="Output file path (default: data/generated/synthetic_events.json)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "jsonl"],
        default="json",
        help="Output format: json array or jsonl lines (default: json)",
    )

    args = parser.parse_args()

    print("============================================================")
    print("CAGED — Synthetic Event Stream Generator")
    print("============================================================")
    print(f"Users       : {args.users:,}")
    print(f"Events      : {args.events:,}")
    print(f"Seed        : {args.seed}")
    print(f"Duration    : {args.duration} hours")
    print(f"Output File : {args.output}")
    print("------------------------------------------------------------")

    config = EventGeneratorConfig(
        num_users=args.users,
        num_events=args.events,
        seed=args.seed,
        duration_hours=args.duration,
        start_time=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
    )

    generator = EventGenerator(config)
    print(f"[*] Initialized {len(generator.users):,} synthetic user profiles across segments:")
    
    # Calculate user breakdown per segment
    segment_counts = {}
    for u in generator.users:
        segment_counts[u.segment.value] = segment_counts.get(u.segment.value, 0) + 1
    for seg, count in segment_counts.items():
        print(f"    - {seg:<15}: {count:,} users ({count/len(generator.users)*100:.1f}%)")

    print("[*] Generating event stream...")
    events = generator.generate_events(policy_state="pre_policy")
    print(f"[+] Successfully generated {len(events):,} validated events.")

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    print(f"[*] Writing to {args.output}...")
    if args.format == "jsonl":
        with open(args.output, "w", encoding="utf-8") as f:
            for evt in events:
                f.write(evt.model_dump_json() + "\n")
    else:
        dict_events = [evt.model_dump(mode="json") for evt in events]
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(dict_events, f, indent=2)

    print(f"[✓] Completed dataset generation: {args.output}")
    print("============================================================")


if __name__ == "__main__":
    main()
