"""
Configurable Metric Aggregator Module for CAGED.
"""

from typing import Dict, List, Optional, Tuple
from app.ingestion.models import EngagementEvent, MetricType
from app.metrics.rolling_window import RollingTimeWindow, WindowStatistics

DEFAULT_SUPPORTED_WINDOWS: List[int] = [60, 300, 900, 3600]  # 1m, 5m, 15m, 1h


class MetricAggregator:
    """
    Stateful metric aggregator maintaining configurable rolling time windows
    across all supported behavioral engagement metrics.
    """

    def __init__(self, supported_windows: Optional[List[int]] = None):
        self.supported_windows = supported_windows or DEFAULT_SUPPORTED_WINDOWS.copy()
        
        # Maps (metric_type, window_seconds) -> RollingTimeWindow
        self.windows: Dict[Tuple[MetricType, int], RollingTimeWindow] = {}
        self._init_windows()

    def _init_windows(self) -> None:
        """Instantiates rolling time window objects for all metrics and window sizes."""
        for metric in MetricType:
            for window_sec in self.supported_windows:
                key = (metric, window_sec)
                self.windows[key] = RollingTimeWindow(metric_type=metric, window_seconds=window_sec)

    def update(self, event: EngagementEvent) -> None:
        """
        Updates all rolling windows associated with the event's metric type.
        
        Args:
            event: Validated EngagementEvent instance.
        """
        metric = event.metric_type
        for window_sec in self.supported_windows:
            key = (metric, window_sec)
            if key in self.windows:
                self.windows[key].add(
                    timestamp=event.timestamp,
                    value=event.value,
                    user_hash=event.user_hash,
                )

    def update_batch(self, events: List[EngagementEvent]) -> None:
        """
        Updates the aggregator with a batch of events.
        """
        for event in events:
            self.update(event)

    def get_metric_value(self, metric: MetricType, window_seconds: int = 300) -> float:
        """
        Returns the current aggregated total value for a metric in the given window.
        """
        stats = self.get_statistics(metric=metric, window_seconds=window_seconds)
        return stats.total_value

    def get_statistics(self, metric: MetricType, window_seconds: int = 300) -> WindowStatistics:
        """
        Retrieves WindowStatistics for a specific metric and window size.
        """
        key = (metric, window_seconds)
        if key not in self.windows:
            # Fallback window if non-standard size requested
            rw = RollingTimeWindow(metric_type=metric, window_seconds=window_seconds)
            return rw.compute_statistics()
        
        return self.windows[key].compute_statistics()

    def get_all_statistics(self, window_seconds: int = 300) -> Dict[MetricType, WindowStatistics]:
        """
        Returns WindowStatistics for all metrics for a given window size.
        """
        result: Dict[MetricType, WindowStatistics] = {}
        for metric in MetricType:
            result[metric] = self.get_statistics(metric=metric, window_seconds=window_seconds)
        return result

    def reset(self) -> None:
        """Resets all rolling windows."""
        self.windows.clear()
        self._init_windows()
