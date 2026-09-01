# CAGED — System Architecture Document

## 1. Executive Summary

**CAGED (Causal Analysis for Guaranteed Engagement Degradation)** is a real-time, privacy-preserving statistical framework designed to continuously monitor privacy-safe user engagement event streams and detect whether engagement degradation occurs following a social-platform policy adjustment.

The core of CAGED is **not** an ML application; rather, it is built on:
- Streaming analytics and time-series adaptive baselines
- Memory-efficient sketch-based data aggregation (Count-Min Sketch, HyperLogLog)
- Statistical degradation detection (Z-score deviations, multi-metric composite scoring)
- Streaming user segmentation (behavioral feature vectors and online clustering)
- False-alarm control (pre-policy noise calibration, bootstrap thresholds, CI estimation)
- Interpretable reporting, alerting, and interactive visual dashboards

---

## 2. High-Level System Architecture

```text
Synthetic Social Platform (Simulator)
        │
        ▼
Synthetic Event Generator
        │
        ▼
Privacy & Data-Minimization Layer
        │
        ▼
Event Ingestion (Async Queue / Future Kafka Adapter)
        │
        ▼
Preprocessing & Validation Engine
        │
        ▼
Metric Extraction Engine
        │
        ├───────────────────────────────────────┐
        ▼                                       ▼
Sketch Aggregation                     User Segmentation
(Count-Min Sketch / HyperLogLog)       (Online Clustering)
        │                                       │
        ▼                                       │
Adaptive Baseline Engine                        │
(Exponential Smoothing / ARIMA)                 │
        │                                       │
        ├───────────────────────────────────────┘
        ▼
Policy Trigger & Timeline Registry
        │
        ▼
Freeze Pre-Policy Baseline (Counterfactual Reference)
        │
        ▼
Post-Policy Stream Monitoring
        │
        ▼
Statistical Degradation Detector (Z-Scores, Variance Bounds)
        │
        ▼
Multi-Metric Composite Degradation Score
        │
        ├───────────────────────────────┐
        ▼                               ▼
 Normal / Stable                    Degraded State
                                        │
                                        ▼
                             Segment-Level Localization
                                        │
                                        ▼
                             Optional ML Prediction (XGBoost)
                                        │
                                        ▼
                             Alert & Reporting Engines
                                        │
                                        ▼
                             FastAPI REST / WebSocket API
                                        │
                                        ▼
                             React + TypeScript Dashboard
```

---

## 3. Core Subsystem Responsibilities

### 3.1 Privacy & Minimization Layer
- **Principle**: "Measure behavior, not private content."
- **Function**: Filters all incoming events against strict privacy policies.
- **Rules**:
  - Enforces pseudonymous hashing (`user_hash`) rather than raw user IDs.
  - Strips/rejects forbidden fields (private messages, credentials, location, contact lists, PII).
  - Validates event timestamps and allowable metric types (`like`, `comment`, `share`, `click`, `session`, `session_duration`, `content_view`).

### 3.2 Event Ingestion & Streaming Adapter
- **Function**: Asynchronously ingests validated events from the synthetic platform stream.
- **Design**:
  - Abstract `EventStreamProducer` and `EventStreamConsumer` interfaces.
  - Initial implementation uses Python `asyncio.Queue` with configurable backpressure and batch windowing.
  - Modularly decoupled to support swapping in Apache Kafka without altering downstream engines.

### 3.3 Metric & Sketch Aggregation Engine
- **Function**: Computes windowed rolling statistics (1m, 5m, 15m, 1h) and memory-bounded aggregations.
- **Components**:
  - `MetricAggregator`: Manages exact time-window sums, means, variances, and rates.
  - `CountMinSketch`: Frequency estimation with configurable width/depth and deterministic hash functions.
  - `HyperLogLog`: Cardinality estimation for unique active user counting.

### 3.4 Adaptive Baseline & Policy Freeze Engine
- **Function**: Learns non-degraded baseline behavior using pre-policy data.
- **Components**:
  - `BaselineModel`: Implements Exponential Smoothing (and optional lightweight ARIMA) to model trend, seasonality, and variance.
  - `PolicyRegistry` & `PolicyTrigger`: Tracks policy events $T_0$.
  - `BaselineSnapshotter`: Freezes the pre-policy baseline state at $T_0$ to serve as a pure counterfactual reference, preventing post-policy degradation from contaminating expectations.

### 3.5 Statistical Degradation Detector & Multi-Metric Scoring
- **Function**: Formally tests post-policy observed metrics against frozen baseline expectations.
- **Formulas**:
  - Per-metric deviation: $D_t = E_t - O_t$
  - Z-score: $Z_k = \frac{D_k}{\sigma_k}$ (where only $Z_k > 0$ represents degradation)
  - Multi-metric composite score: $S = \sum_{k} \max(Z_k, 0)^2$
  - False-alarm control: Bootstrap-calibrated noise thresholds based on `target_false_alarm_rate`.

### 3.6 User Segmentation & Root Cause Localization
- **Function**: Identifies which user communities (e.g. casual, regular, heavy, content-focused) suffer disproportionate engagement drops.
- **Technique**: Constructs behavioral feature vectors (session frequency, metric proportions, category preferences) without private content and applies online MiniBatch clustering.

### 3.7 Alerting, Reporting & ML Extensions
- **Function**: Summarizes detection results, sends structured alerts, and offers optional predictive analysis.
- **ML Extension**: Independent XGBoost classifier/regressor that predicts future degradation probability based on early post-policy signals. Must remain strictly isolated from the core statistical detector.

---

## 4. Canonical Data Model

### EngagementEvent (Pydantic Schema)
```python
class EngagementEvent(BaseModel):
    event_id: str
    user_hash: str
    metric_type: Literal["like", "comment", "share", "click", "session", "session_duration", "content_view"]
    value: float = 1.0
    timestamp: datetime
    content_category: str
    segment_metadata: Optional[Dict[str, Any]] = None
    policy_state: Optional[str] = "pre_policy"
```

### PolicyEvent (Pydantic Schema)
```python
class PolicyEvent(BaseModel):
    policy_id: str
    policy_name: str
    timestamp: datetime
    description: str
    target_metric: Optional[str] = None
    target_segment: Optional[str] = None
```

---

## 5. Storage Strategy
- **Application State**: PostgreSQL database (or SQLite for initial local development) for policy timelines, baseline snapshots, alert history, and aggregated reports.
- **In-Memory Cache & Streams**: Memory-mapped data structures, rolling queues, and sketch tables for high-throughput stream processing.

---

## 6. Frontend & API Layer
- **API**: FastAPI providing REST endpoints for system health, streaming control, policy management, metric inspection, segment breakdowns, and SSE/WebSocket real-time metrics.
- **Dashboard**: React + TypeScript SPA built with Vite, featuring interactive Plotly/Recharts visualization of expected vs. observed metrics, Z-score timelines, composite degradation alerts, and segment heatmaps.
