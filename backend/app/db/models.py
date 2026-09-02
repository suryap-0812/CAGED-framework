"""
SQLAlchemy Persistent Analytical ORM Models for CAGED (Zero Private Content).
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PolicyEventDB(Base):
    __tablename__ = "policy_events"

    policy_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    policy_name: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    impact_factor: Mapped[float] = mapped_column(Float, default=0.80)
    target_metric: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_segment: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class BaselineSnapshotDB(Base):
    __tablename__ = "baseline_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    policy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String(64), nullable=False)
    frozen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_type: Mapped[str] = mapped_column(String(64), nullable=False)
    model_state_json: Mapped[str] = mapped_column(Text, nullable=False)


class DegradationAlertDB(Base):
    __tablename__ = "alerts"

    alert_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    policy_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)
    max_z_score: Mapped[float] = mapped_column(Float, nullable=False)
    p_value: Mapped[float] = mapped_column(Float, nullable=False)
    most_degraded_segment: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)


class DegradationReportDB(Base):
    __tablename__ = "reports"

    report_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    policy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    overall_composite_score: Mapped[float] = mapped_column(Float, nullable=False)
    overall_is_degraded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_localized: Mapped[bool] = mapped_column(Boolean, default=False)
    report_json: Mapped[str] = mapped_column(Text, nullable=False)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)


class ExperimentDB(Base):
    __tablename__ = "experiments"

    experiment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_degraded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="COMPLETED")
