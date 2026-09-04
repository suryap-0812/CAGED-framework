"""
5-Minute Fixed Window Aggregator and Rate Normalization Engine for CAGED.
Converts raw EngagementEvent streams into standardized 5-minute rate metrics.
"""

from datetime import datetime, timedelta, timezone
import math
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.ingestion.models import EngagementEvent, MetricType


class WindowedMetricPoint(BaseModel):
    """Normalized metrics aggregated over a single 5-minute window."""

    window_start: datetime = Field(..., description="UTC start of 5-minute window")
    window_end: datetime = Field(..., description="UTC end of 5-minute window")
    window_index: int = Field(..., description="Sequential window index")
    
    views_count: int = Field(default=0, description="Total views in window")
    likes_count: int = Field(default=0, description="Total likes in window")
    comments_count: int = Field(default=0, description="Total comments in window")
    shares_count: int = Field(default=0, description="Total shares in window")
    clicks_count: int = Field(default=0, description="Total clicks in window")
    
    unique_active_users: int = Field(default=0, description="Unique active user count")
    avg_session_duration_sec: float = Field(default=0.0, description="Mean session duration in seconds")

    # Rate-normalized metrics
    views_per_min: float = Field(default=0.0, description="View throughput per minute")
    likes_per_view: float = Field(default=0.0, description="Likes per view ratio")
    comments_per_view: float = Field(default=0.0, description="Comments per view ratio")
    shares_per_view: float = Field(default=0.0, description="Shares per view ratio")
    clicks_per_view: float = Field(default=0.0, description="Clicks per view ratio")

    # Segment-specific metrics breakdown (segment_id -> metric_type -> value)
    segment_breakdown: Dict[str, Dict[str, float]] = Field(
        default_factory=dict, description="Metric breakdown by user segment"
    )
    category_breakdown: Dict[str, Dict[str, float]] = Field(
        default_factory=dict, description="Metric breakdown by content category"
    )

    def get_metric_value(self, metric_type: MetricType) -> float:
        """Helper to retrieve normalized rate value for a given MetricType."""
        if metric_type == MetricType.VIEW:
            return self.views_per_min
        elif metric_type == MetricType.LIKE:
            return self.likes_per_view
        elif metric_type == MetricType.COMMENT:
            return self.comments_per_view
        elif metric_type == MetricType.SHARE:
            return self.shares_per_view
        elif metric_type == MetricType.CLICK:
            return self.clicks_per_view
        elif metric_type == MetricType.SESSION_DURATION:
            return self.avg_session_duration_sec
        return 0.0


class WindowAggregator:
    """
    Aggregates continuous streams of EngagementEvent objects into 5-minute fixed windows.
    """

    def __init__(self, window_size_minutes: int = 5):
        self.window_size_sec = window_size_minutes * 60.0
        self.window_size_minutes = float(window_size_minutes)

    def aggregate_stream(
        self,
        events: List[EngagementEvent],
        start_time: Optional[datetime] = None,
    ) -> List[WindowedMetricPoint]:
        """
        Aggregates events into 5-minute windowed metric points.
        """
        if not events:
            return []

        sorted_events = sorted(events, key=lambda e: e.timestamp)
        t_start = start_time or sorted_events[0].timestamp
        if t_start.tzinfo is None:
            t_start = t_start.replace(tzinfo=timezone.utc)

        t_end = sorted_events[-1].timestamp
        if t_end.tzinfo is None:
            t_end = t_end.replace(tzinfo=timezone.utc)

        total_span_sec = (t_end - t_start).total_seconds()
        num_windows = max(1, math.ceil(total_span_sec / self.window_size_sec))

        # Bucket events into window indices
        windows_raw: List[Dict] = []
        for w_idx in range(num_windows):
            w_s = t_start + timedelta(seconds=w_idx * self.window_size_sec)
            w_e = w_s + timedelta(seconds=self.window_size_sec)
            windows_raw.append({
                "window_start": w_s,
                "window_end": w_e,
                "window_index": w_idx,
                "events": [],
            })

        for evt in sorted_events:
            evt_time = evt.timestamp
            if evt_time.tzinfo is None:
                evt_time = evt_time.replace(tzinfo=timezone.utc)

            offset_sec = (evt_time - t_start).total_seconds()
            w_idx = int(offset_sec // self.window_size_sec)
            if 0 <= w_idx < len(windows_raw):
                windows_raw[w_idx]["events"].append(evt)

        metric_points: List[WindowedMetricPoint] = []

        for w in windows_raw:
            evts = w["events"]
            views = sum(1 for e in evts if e.metric_type == MetricType.VIEW)
            likes = sum(1 for e in evts if e.metric_type == MetricType.LIKE)
            comments = sum(1 for e in evts if e.metric_type == MetricType.COMMENT)
            shares = sum(1 for e in evts if e.metric_type == MetricType.SHARE)
            clicks = sum(1 for e in evts if e.metric_type == MetricType.CLICK)
            
            sessions = [e.value for e in evts if e.metric_type == MetricType.SESSION_DURATION]
            avg_session = float(sum(sessions) / len(sessions)) if sessions else 0.0
            
            users = set(e.user_hash for e in evts if e.user_hash)

            # Calculate rates
            v_rate = views / self.window_size_minutes
            v_denom = max(1, views)
            l_rate = likes / v_denom
            c_rate = comments / v_denom
            s_rate = shares / v_denom
            cl_rate = clicks / v_denom

            # Segment breakdown
            seg_data: Dict[str, Dict[str, float]] = {}
            for e in evts:
                seg = e.segment_metadata.get("user_segment", "all") if e.segment_metadata else "all"
                if seg not in seg_data:
                    seg_data[seg] = {"views": 0, "likes": 0, "comments": 0, "shares": 0, "clicks": 0}
                m_str = e.metric_type.value
                if m_str in seg_data[seg]:
                    seg_data[seg][m_str] += 1

            # Category breakdown
            cat_data: Dict[str, Dict[str, float]] = {}
            for e in evts:
                cat = e.content_category or "general"
                if cat not in cat_data:
                    cat_data[cat] = {"views": 0, "likes": 0, "comments": 0, "shares": 0, "clicks": 0}
                m_str = e.metric_type.value
                if m_str in cat_data[cat]:
                    cat_data[cat][m_str] += 1

            metric_points.append(
                WindowedMetricPoint(
                    window_start=w["window_start"],
                    window_end=w["window_end"],
                    window_index=w["window_index"],
                    views_count=views,
                    likes_count=likes,
                    comments_count=comments,
                    shares_count=shares,
                    clicks_count=clicks,
                    unique_active_users=len(users),
                    avg_session_duration_sec=round(avg_session, 2),
                    views_per_min=round(v_rate, 4),
                    likes_per_view=round(l_rate, 4),
                    comments_per_view=round(c_rate, 4),
                    shares_per_view=round(s_rate, 4),
                    clicks_per_view=round(cl_rate, 4),
                    segment_breakdown=seg_data,
                    category_breakdown=cat_data,
                )
            )

        return metric_points
