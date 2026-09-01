# CAGED — Development Plan & Phase Roadmap

## 1. Project Overview & Implementation Roadmap

CAGED is built incrementally across 20 distinct phases (Phase 0 to Phase 19). Each phase represents a self-contained engineering milestone with explicit inputs, outputs, test requirements, and validation criteria.

---

## 2. Phase-by-Phase Roadmap

### Phase 0 — Repository Audit & Technical Design *(Current Phase)*
- **Goal**: Audit repository, establish project conventions, design system architecture, create development roadmap and dependency specifications.
- **Deliverables**: `docs/architecture.md`, `docs/development-plan.md`, `README.md`, Python & Node dependency plans.
- **Validation**: Project structure documented, dependencies specified, clean architecture alignment.

### Phase 1 — Project Foundation
- **Goal**: Minimal runnable backend (FastAPI) and frontend (React + TypeScript + Vite) skeleton.
- **Deliverables**: `/health` API endpoint, FastAPI configuration, Pydantic schemas, Uvicorn setup, basic Vite frontend with health check page.
- **Validation**: `pytest` passes for backend startup and `/health` response; frontend dev server builds without errors.

### Phase 2 — Privacy-Safe Event Model
- **Goal**: Implement `EngagementEvent` canonical model and privacy-enforcement layer.
- **Deliverables**: Ingestion models, privacy sanitizer, metric type validators, `docs/privacy.md`.
- **Validation**: Reject forbidden PII fields, accept valid events, enforce pseudonymization.

### Phase 3 — Synthetic Social Platform Event Generator
- **Goal**: Configurable synthetic event generator for reproducing platform streams.
- **Deliverables**: User profile generator, temporal event simulator script (`scripts/generate_events.py`).
- **Validation**: Seed reproducibility, realistic metric distributions, zero private fields.

### Phase 4 — Event Ingestion + Stream Processing
- **Goal**: Asynchronous continuous event producer/consumer pipeline.
- **Deliverables**: Async event queue, batch/window processing, throughput benchmark utilities.
- **Validation**: High-throughput processing without memory leaks, clean queue drain/backpressure handling.

### Phase 5 — Metric Engine
- **Goal**: Convert event streams into rolling time-series metrics.
- **Deliverables**: `MetricAggregator` supporting rolling windows (1m, 5m, 15m, 1h), mean, variance, standard deviation calculations.
- **Validation**: Exact numerical verification against small control datasets, window sliding accuracy.

### Phase 6 — Count-Min Sketch
- **Goal**: Memory-efficient frequency estimation structure.
- **Deliverables**: `CountMinSketch` implementation with configurable width/depth and deterministic hashing.
- **Validation**: Evaluate error bounds against exact dictionary counts in `experiments/evaluation/sketch_accuracy.py`.

### Phase 7 — HyperLogLog
- **Goal**: Cardinality estimation for approximate unique-user counts.
- **Deliverables**: `HyperLogLog` class with configurable precision and register merging.
- **Validation**: Measure relative error and memory efficiency against exact unique count benchmarks.

### Phase 8 — Adaptive Baseline Engine
- **Goal**: Time-series baseline modeling for normal engagement before policy changes.
- **Deliverables**: `BaselineModel` supporting Exponential Smoothing and rolling variance estimation.
- **Validation**: Predict expected metrics on synthetic stationary, trend, and seasonal streams with minimal residual error.

### Phase 9 — Policy Event System
- **Goal**: Formal representation and registry of platform policy modifications.
- **Deliverables**: `PolicyEvent`, `PolicyRegistry`, `PolicyTimeline`, simulator trigger integration.
- **Validation**: Policy triggers accurately injected into event streams without providing ground-truth degradation values to CAGED.

### Phase 10 — Pre-Policy Baseline Freezing
- **Goal**: Counterfactual reference freezing at policy trigger time $T_0$.
- **Deliverables**: `BaselineSnapshotter`, frozen state storage, multi-policy handling.
- **Validation**: Pre-policy baseline learned prior to $T_0$, snapshot frozen at $T_0$, post-policy data strictly prevented from mutating frozen baseline.

### Phase 11 — Statistical Degradation Detector
- **Goal**: Core statistical test comparing post-policy observations to frozen baseline expectations.
- **Deliverables**: `StatisticalDegradationDetector`, Z-score computation, non-zero variance safeguards.
- **Validation**: Unit tests on zero, low, and high degradation scenarios, noise resilience.

### Phase 12 — Multi-Metric Degradation Score
- **Goal**: Composite degradation scoring across multiple engagement metrics.
- **Deliverables**: `MultiMetricDetector` producing composite score $S = \sum \max(Z_k, 0)^2$ and identifying top contributing metrics.
- **Validation**: Multi-metric sensitivity tests, metric breakdown reporting.

### Phase 13 — False-Alarm Control
- **Goal**: Statistically rigorous false-alarm rate calibration.
- **Deliverables**: Pre-policy noise calibration, bootstrap threshold estimation, confidence intervals.
- **Validation**: Measure False Positive Rate (FPR), True Positive Rate (TPR), and detection latency.

### Phase 14 — Streaming User Segmentation
- **Goal**: Online user behavioral profiling and clustering.
- **Deliverables**: Behavioral feature extractor, `MiniBatchKMeans` streaming segmentation.
- **Validation**: Stable cluster assignments without using private content.

### Phase 15 — Segment-Level Degradation
- **Goal**: Disproportionate degradation detection across specific user segments.
- **Deliverables**: `SegmentDegradationAnalyzer`, segment Z-scores, localization ranker.
- **Validation**: Correctly isolate localized policy impacts (e.g. video-heavy users affected while text users remain stable).

### Phase 16 — Optional ML Degradation Predictor
- **Goal**: Predictive ML model (XGBoost) for early degradation forecasting.
- **Deliverables**: Feature generator, XGBoost classifier/regressor, evaluation suite.
- **Validation**: Precision/Recall, ROC-AUC metrics; verify complete architectural isolation from core statistical detector.

### Phase 17 — Alert Engine + Report Engine
- **Goal**: Automated alert generation and analytical report compilation.
- **Deliverables**: `AlertEngine`, `ReportEngine` (JSON, Markdown, PDF outputs).
- **Validation**: Accurate severity classification, actionable summaries, schema correctness.

### Phase 18 — Interactive Analytics Dashboard
- **Goal**: Complete React + TypeScript monitoring dashboard.
- **Deliverables**: Time-series charts, policy event overlay, segment breakdown heatmaps, alert notifications.
- **Validation**: Responsive UI rendering, real-time API integration, clean navigation.

### Phase 19 — End-to-End Experimental Validation
- **Goal**: Full system benchmark and experimental verification.
- **Deliverables**: Benchmark scripts, scenario evaluation, final report artifacts.
- **Validation**: Comprehensive end-to-end integration test execution, statistical rigor verification.

---

## 3. Technology Stack & Dependency Plan

### Backend Dependencies (`backend/pyproject.toml` or `backend/requirements.txt`)
```text
# Web Framework & API
fastapi>=0.110.0
uvicorn[standard]>=0.28.0
pydantic>=2.6.0
pydantic-settings>=2.2.0

# Data Science & Statistics
numpy>=1.26.0
pandas>=2.2.0
scipy>=1.12.0
statsmodels>=0.14.0
scikit-learn>=1.4.0
xgboost>=2.0.0

# Database & Storage
sqlalchemy>=2.0.0
asyncpg>=0.29.0
psycopg2-binary>=2.9.9
alembic>=1.13.0

# Testing & Quality
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
httpx>=0.27.0
```

### Frontend Dependencies (`frontend/package.json`)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.22.0",
    "recharts": "^2.12.0",
    "lucide-react": "^0.344.0",
    "axios": "^1.6.7"
  },
  "devDependencies": {
    "@types/react": "^18.2.64",
    "@types/react-dom": "^18.2.21",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.3.3",
    "vite": "^5.1.5"
  }
}
```

---

## 4. Coding Conventions & Best Practices

1. **Python Quality**:
   - Python 3.12+ features, explicit type hints for all function arguments and returns.
   - Pydantic v2 for data validation and schema definitions.
   - Standardized exception handling and structured JSON logging.
   - 100% docstring coverage for statistical algorithms detailing underlying math.

2. **Frontend Quality**:
   - Clean React component hierarchy with TypeScript interfaces for all props and state.
   - Modular CSS / Vanilla CSS styling with consistent design tokens.
   - Proper API request state handling (loading, error, data).

3. **Privacy By Design**:
   - Zero tolerance for processing private content (messages, photos, credentials, PII).
   - Strict pseudonymization of user identifiers using SHA-256 hashes with optional salt.

4. **Testing Rigor**:
   - Deterministic test seeds for random processes.
   - Unit tests for all mathematical and statistical modules (`pytest`).
   - Absolute non-fabrication of test or benchmark results.
