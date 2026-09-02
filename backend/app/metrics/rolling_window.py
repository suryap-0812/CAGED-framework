"""
Rolling Time Window Data Structure & Statistical Calculations for CAGED.
"""

from collections import deque
from datetime import datetime, timedelta, timezone
import math
from typing import Deque, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from app.ingestion.models import MetricType

# Representation of a single metric observation inside window
# (timestamp_utc, numerical_value, user_hash)
Observation = Tuple[datetime, float, str]


class WindowStatistics(BaseModel):
    """Container for rolling time-window statistical aggregations."""

    metric_type: MetricType = Field(..., description="Target engagement metric")
    window_seconds: int = Field(..., description="Rolling window duration in seconds")
    count: int = Field(default=0, description="Total event count in window")
    total_value: float = Field(default=0.0, description="Sum of metric values")
    mean: float = Field(default=0.0, description="Arithmetic mean of values")
    variance: float = Field(default=0.0, description="Sample variance (0 if count <= 1)")
    std_dev: float = Field(default=0.0, description="Standard deviation")
    rate_per_sec: float = Field(default=0.0, description="Event rate per second")
    unique_users_count: int = Field(default=0, description="Unique active users in window")
    window_start: datetime = Field(..., description="Earliest UTC boundary of window")
    window_end: datetime = Field(..., description="Latest UTC boundary of window")


class RollingTimeWindow:
    """
    Sliding time window maintaining timestamped observations and computing
    exact streaming summary statistics.
    """

    def __init__(self, metric_type: MetricType, window_seconds: int = 300):
        self.metric_type = metric_type
        self.window_seconds = window_seconds
        self.observations: Deque[Observation] = deque()
        self.latest_timestamp: Optional[datetime] = None

    def add(self, timestamp: datetime, value: float, user_hash: str) -> None:
        """
        Adds a new metric observation and prunes expired events.
        
        Args:
            timestamp: Event UTC timestamp.
            value: Quantitative metric value.
            user_hash: Pseudonymous user hash.
        """
        # Ensure UTC timezone
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = timestamp.astimezone(timezone.utc)

        if self.latest_timestamp is None or timestamp > self.latest_timestamp:
            self.latest_timestamp = timestamp

        self.observations.append((timestamp, value, user_hash))
        self.prune(reference_time=self.latest_timestamp)

    def prune(self, reference_time: Optional[datetime] = None) -> None:
        """
        Evicts observations older than window_seconds relative to reference_time.
        """
        ref = reference_time or self.latest_timestamp
        if ref is None or not self.observations:
            return

        cutoff = ref - timedelta(seconds=self.window_seconds)
        while self.observations and self.observations[0][0] < cutoff:
            self.observations.popleft()

    def compute_statistics(self, reference_time: Optional[datetime] = None) -> WindowStatistics:
        """
        Computes exact rolling statistics over currently active window observations.
        
        Returns:
            WindowStatistics instance.
        """
        ref_end = reference_time or self.latest_timestamp or datetime.now(timezone.utc)
        ref_start = ref_end - timedelta(seconds=self.window_seconds)
        
        self.prune(reference_time=ref_end)

        n = len(self.observations)
        if n == 0:
            return WindowStatistics(
                metric_type=self.metric_type,
                window_seconds=self.window_seconds,
                count=0,
                total_value=0.0,
                mean=0.0,
                variance=0.0,
                std_dev=0.0,
                rate_per_sec=0.0,
                unique_users_count=0,
                window_start=ref_start,
                window_end=ref_end,
            )

        total_val = 0.0
        unique_users: Set[str] = set()
        values: List[float] = []

        for _, val, u_hash in self.observations:
            total_val += val
            values.append(val)
            unique_users.add(u_hash)

        mean_val = total_val / n
        rate = total_val / float(self.window_seconds)

        # Sample variance calculation
        if n > 1:
            squared_diff_sum = sum((v - mean_val) ** 2 for v in values)
            variance_val = squared_diff_sum / (n - 1)
            std_dev_val = math.sqrt(variance_val)
        else:
            variance_val = 0.0
            std_dev_val = 0.0

        return WindowStatistics(
            metric_type=self.metric_type,
            window_seconds=self.window_seconds,
            count=n,
            total_value=round(total_val, 4),
            mean=round(mean_val, 4),
            variance=round(variance_val, 6),
            std_dev=round(std_dev_val, 6),
            rate_per_sec=round(rate, 4),
            unique_users_count=len(unique_users),
            window_start=ref_start,
            window_end=ref_end,
        )
