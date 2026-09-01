# MASTER PROMPT — CAGED

You are a senior Data Science + Backend + Streaming Systems + Statistical Computing engineer.

You will build a complete production-quality prototype of:

CAGED
"Causal Analysis for Guaranteed Engagement Degradation"

Project type:
Real-time statistical/algorithmic framework implemented as a complete monitoring system.

IMPORTANT:
CAGED is NOT primarily an ML application.
Its core is:
- streaming analytics
- statistical modeling
- time-series baselines
- sketch-based aggregation
- statistical anomaly/degradation detection
- multi-metric analysis
- streaming user segmentation
- optional machine-learning prediction

The final system must demonstrate how engagement changes after a simulated social-platform policy adjustment can be detected, statistically validated, localized, and reported.

============================================================
# 1. CORE PROJECT IDEA
============================================================

The system continuously receives privacy-safe user-engagement events.

Examples:

- likes
- comments
- shares
- clicks
- posts
- content views
- sessions
- session duration

The system must NOT process private user content.

Do NOT collect or process:

- private messages
- message contents
- passwords
- private documents
- private photos
- private videos
- contact lists
- exact personal location
- unnecessary personally identifiable information

Principle:

"Measure behavior, not private content."

The system should use pseudonymous identifiers only when individual-level processing is genuinely necessary.

============================================================
# 2. HIGH-LEVEL ARCHITECTURE
============================================================

Build the following architecture:

Synthetic Social Platform
        |
        v
Synthetic Event Generator
        |
        v
Privacy/Data-Minimization Layer
        |
        v
Event Ingestion
        |
        v
Preprocessing
        |
        v
Metric Extraction
        |
        +-----------------------------+
        |                             |
        v                             v
Sketch Aggregation              User Segmentation
        |                             |
        v                             |
Adaptive Baseline                    |
        |                             |
        +-------------+---------------+
                      |
                      v
                Policy Trigger
                      |
                      v
             Freeze Pre-Policy Baseline
                      |
                      v
             Post-Policy Monitoring
                      |
                      v
             Statistical Detection
                      |
                      v
              Multi-Metric Score
                      |
                +-----+-----+
                |           |
                v           v
             Normal      Degradation
                            |
                            v
                    Segment-Level Analysis
                            |
                            v
                    Optional ML Analysis
                            |
                            v
                       Alert Engine
                            |
                            v
                       Report Engine
                            |
                            v
                       REST API
                            |
                            v
                       Dashboard

============================================================
# 3. TECHNOLOGY STACK
============================================================

Use the following stack unless there is a strong technical reason to change it.

Backend:
- Python 3.12+
- FastAPI
- Pydantic
- Uvicorn

Data Science:
- NumPy
- Pandas
- SciPy
- Statsmodels
- Scikit-learn

Optional ML:
- XGBoost

Streaming:
- Initially implement an internal asynchronous event-stream simulator.
- Structure the architecture so Apache Kafka can be added later.
- Do NOT introduce Kafka in the first implementation phase unless required.

Storage:
- PostgreSQL for persistent application data.
- SQLite may be used during initial development if necessary, but the architecture must permit PostgreSQL.

Frontend:
- React
- TypeScript
- Vite
- modern component architecture
- charting library such as Plotly or Recharts

Testing:
- pytest
- pytest-asyncio where required

Development:
- Git
- .env configuration
- Docker/Docker Compose where useful

============================================================
# 4. IMPORTANT ENGINEERING RULE
============================================================

DO NOT BUILD EVERYTHING AT ONCE.

The project MUST be implemented in phases.

Each phase must:

1. inspect the current repository
2. understand what has already been implemented
3. implement only the current phase
4. run tests
5. run the application/components
6. validate outputs
7. fix errors
8. document what was implemented
9. provide a concise completion summary
10. STOP

Do NOT automatically continue to the next phase.

Wait for the user to explicitly say:

"Continue to Phase N"

before beginning the next phase.

Never overwrite working code unnecessarily.

Never create duplicate modules because a similar module already exists.

Before writing code, inspect the repository structure.

============================================================
# 5. DEVELOPMENT PRINCIPLES
============================================================

Follow these principles:

- modular architecture
- clean separation of concerns
- type hints
- meaningful names
- reusable functions
- configuration-driven behavior
- deterministic tests where possible
- no hard-coded secrets
- no hard-coded absolute paths
- no unnecessary dependencies
- proper exception handling
- structured logging
- unit tests for statistical logic
- integration tests for pipelines
- reproducible experiments
- clear documentation

Do NOT use fake implementations disguised as completed functionality.

If a component is temporarily mocked, clearly label it as a mock and document what remains.

Do NOT silently simplify mathematical/statistical components.

============================================================
# 6. PROJECT DIRECTORY
============================================================

Use a structure approximately like:

caged/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   │
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   └── schemas/
│   │   │
│   │   ├── core/
│   │   │   ├── logging.py
│   │   │   └── exceptions.py
│   │   │
│   │   ├── ingestion/
│   │   ├── preprocessing/
│   │   ├── metrics/
│   │   ├── sketches/
│   │   ├── baselines/
│   │   ├── policy/
│   │   ├── detection/
│   │   ├── segmentation/
│   │   ├── ml/
│   │   ├── reporting/
│   │   ├── simulation/
│   │   ├── storage/
│   │   └── services/
│   │
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── charts/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── types/
│   │   └── utils/
│   └── tests/
│
├── experiments/
│   ├── scenarios/
│   ├── notebooks/
│   ├── results/
│   └── evaluation/
│
├── data/
│   ├── generated/
│   └── schemas/
│
├── docs/
│
├── scripts/
│
├── docker/
│
├── docker-compose.yml
├── README.md
├── .env.example
└── .gitignore

Adapt this structure if the existing repository already has a better organization.

============================================================
# 7. DOMAIN MODEL
============================================================

Define a canonical EngagementEvent.

Conceptually:

EngagementEvent:
- event_id
- pseudonymous_user_id
- metric_type
- value
- timestamp
- content_category
- optional segment metadata
- policy_state

Do not include private content.

Example:

{
    "event_id": "evt_001",
    "user_hash": "a81f...",
    "metric_type": "like",
    "value": 1,
    "timestamp": "...",
    "content_category": "education"
}

Metric types should be configurable.

Initial metrics:

- likes
- comments
- shares
- clicks
- sessions
- session_duration
- views

============================================================
# 8. PHASE PLAN
============================================================

Implement the project in exactly the following major phases.

------------------------------------------------------------
PHASE 0 — REPOSITORY AUDIT + TECHNICAL DESIGN
------------------------------------------------------------

Goal:

Understand the repository before modifying anything.

Tasks:

- inspect all existing files
- identify current frontend/backend
- identify existing dependencies
- identify existing database configuration
- identify reusable components
- identify conflicts with the CAGED architecture
- create/modify architecture documentation
- create implementation roadmap
- establish coding conventions

Do NOT implement the complete application.

Deliver:

- architecture.md
- development-plan.md
- updated README
- dependency plan

Validation:

- repository structure is understood
- no unnecessary files created
- architecture is internally consistent

STOP.

------------------------------------------------------------
PHASE 1 — PROJECT FOUNDATION
------------------------------------------------------------

Goal:

Create the minimal runnable backend/frontend structure.

Backend:

- FastAPI application
- configuration system
- health endpoint
- logging
- Pydantic schemas
- error handling

Frontend:

- React + TypeScript application
- routing
- basic layout
- API service layer
- health-status page

Create:

GET /health

Return:

{
    "status": "ok",
    "service": "caged"
}

Add:

- .env.example
- requirements/package configuration
- README setup instructions

Tests:

- backend startup
- /health
- frontend startup

STOP.

------------------------------------------------------------
PHASE 2 — PRIVACY-SAFE EVENT MODEL
------------------------------------------------------------

Goal:

Implement the canonical event model and privacy/data-minimization layer.

Implement:

- EngagementEvent
- MetricType
- event validation
- pseudonymous ID handling
- event sanitization
- privacy validation

Reject or remove forbidden fields.

Tests must verify:

- valid event accepted
- malformed event rejected
- private-content fields never reach analytical modules
- timestamps validated
- unsupported metric rejected

Create documentation:

docs/privacy.md

Explain:

- data minimization
- pseudonymization
- no private-content processing
- why each collected metric is necessary

STOP.

------------------------------------------------------------
PHASE 3 — SYNTHETIC SOCIAL PLATFORM EVENT GENERATOR
------------------------------------------------------------

Goal:

Create the experimental environment.

This is NOT a real social network.

Build a configurable event simulator.

It must generate:

- users
- user behavior profiles
- content categories
- engagement events
- timestamps
- sessions
- realistic temporal variation

User profiles should include behavioral categories such as:

- casual
- regular
- heavy
- content-focused

Do NOT use real people's information.

Create configurable parameters:

- number of users
- event rate
- metric probabilities
- segment proportions
- time period
- randomness seed

Example:

python scripts/generate_events.py \
    --users 10000 \
    --events 1000000 \
    --seed 42

Generate reproducible datasets.

Tests:

- distribution sanity
- reproducibility
- metric validity
- no private fields
- segment generation

STOP.

------------------------------------------------------------
PHASE 4 — EVENT INGESTION + STREAM PROCESSING
------------------------------------------------------------

Goal:

Process generated events continuously.

Implement:

- asynchronous event producer
- event consumer
- event queue
- batch/window processing
- backpressure handling where appropriate
- structured logging
- throughput measurement

Support:

- single event processing
- batch processing
- time windows

Design interfaces so Kafka can later replace the internal event queue.

Tests:

- events consumed
- ordering behavior documented
- invalid events rejected
- throughput benchmark
- queue behavior

STOP.

------------------------------------------------------------
PHASE 5 — METRIC ENGINE
------------------------------------------------------------

Goal:

Convert events into engagement time series.

Implement:

- metric counters
- rates
- rolling windows
- session statistics
- mean
- variance
- standard deviation
- unique-user approximation interface

Support windows such as:

- 1 minute
- 5 minutes
- 15 minutes
- 1 hour

Metrics must be configurable.

Create:

MetricAggregator

with methods conceptually like:

update(event)
get_current_window()
get_metric_value(metric)
get_statistics(metric)

Tests:

- exact small-dataset calculations
- rolling windows
- variance
- missing values
- boundary timestamps

STOP.

------------------------------------------------------------
PHASE 6 — COUNT-MIN SKETCH
------------------------------------------------------------

Goal:

Implement memory-efficient frequency estimation.

Implement a proper Count-Min Sketch.

Requirements:

- configurable width
- configurable depth
- deterministic hash functions
- update
- estimate
- reset
- serialization if needed

Test against exact counts.

Measure:

- absolute error
- relative error
- memory consumption

Compare:

exact dictionary counting
vs
Count-Min Sketch

Create experiment:

experiments/evaluation/sketch_accuracy.py

STOP.

------------------------------------------------------------
PHASE 7 — HYPERLOGLOG
------------------------------------------------------------

Goal:

Implement approximate unique-user/cardinality estimation.

Implement:

- configurable precision
- add
- estimate
- merge if useful

Validate against exact unique counts.

Measure:

- relative error
- memory usage

Clearly explain why HyperLogLog is used.

STOP.

------------------------------------------------------------
PHASE 8 — ADAPTIVE BASELINE ENGINE
------------------------------------------------------------

Goal:

Learn normal engagement behavior before policy changes.

Implement baseline interface:

BaselineModel

Implement first:

- exponential smoothing

Optionally implement:

- lightweight ARIMA

Baseline must support:

- initialization
- update
- prediction
- variance/error estimation
- confidence interval estimation

Model:

Expected engagement:

E_t = μ_t + η_t

The baseline should account for normal temporal behavior.

Where useful, support:

- trend
- seasonality
- rolling variance

Tests:

- synthetic stationary stream
- trend stream
- seasonal stream
- noise stream

Measure prediction error.

STOP.

------------------------------------------------------------
PHASE 9 — POLICY EVENT SYSTEM
------------------------------------------------------------

Goal:

Represent policy adjustments explicitly.

Create:

PolicyEvent

Fields:

- policy_id
- policy_name
- timestamp
- description
- affected metric/category if applicable

Implement:

PolicyRegistry
PolicyTimeline
PolicyTrigger

The simulator must be able to introduce policy changes.

Examples:

Policy P001:
change engagement probability by -20%

Policy P002:
affect only video-focused users

Policy P003:
affect comments but not likes

Important:

Do not simply tell CAGED the answer.

The policy event only identifies when a policy changed.

CAGED must independently measure the resulting engagement change.

STOP.

------------------------------------------------------------
PHASE 10 — PRE-POLICY BASELINE FREEZING
------------------------------------------------------------

Goal:

Create the counterfactual reference.

Before policy:

baseline learns normal behavior.

At policy time T0:

freeze the appropriate pre-policy baseline.

After T0:

do not contaminate the frozen baseline with post-policy degradation.

Implement:

- baseline snapshot
- policy-time freeze
- baseline retrieval
- multiple policy handling

Tests:

- baseline is learned before T0
- baseline is frozen at T0
- post-policy data does not modify frozen baseline
- multiple policies handled safely

STOP.

------------------------------------------------------------
PHASE 11 — STATISTICAL DEGRADATION DETECTOR
------------------------------------------------------------

Goal:

Implement the core CAGED statistical detector.

For each metric:

D = expected - observed

Then:

Z = D / σ

Only positive degradation should contribute to degradation scoring.

Implement configurable thresholds.

Handle:

- zero variance
- insufficient observations
- missing values
- approximate sketch error
- confidence intervals

Tests must include:

- no degradation
- small degradation
- large degradation
- variance changes
- noisy streams
- zero-variance baseline

STOP.

------------------------------------------------------------
PHASE 12 — MULTI-METRIC DEGRADATION SCORE
------------------------------------------------------------

Goal:

Combine multiple engagement metrics.

Implement:

S = Σ max(Z_k, 0)^2

where k represents engagement metrics.

Create:

MultiMetricDetector

Input:

- metric observations
- expected values
- standard deviations
- threshold

Output:

- composite score
- threshold
- degraded/not degraded
- contributing metrics

Example:

likes Z = 3.1
comments Z = 2.7
shares Z = 3.4

The detector should identify which metrics contributed most.

STOP.

------------------------------------------------------------
PHASE 13 — FALSE-ALARM CONTROL
------------------------------------------------------------

Goal:

Make detection statistically meaningful.

Implement methods as appropriate:

- pre-policy noise calibration
- bootstrap-based threshold estimation
- confidence intervals
- sketch-error considerations
- multiple-comparison correction where required

Allow configuration:

target_false_alarm_rate

Do not arbitrarily hard-code thresholds without explanation.

Create experiments measuring:

- false positive rate
- true positive rate
- detection delay

STOP.

------------------------------------------------------------
PHASE 14 — STREAMING USER SEGMENTATION
------------------------------------------------------------

Goal:

Determine which user communities are affected.

Build user feature vectors from privacy-safe behavioral information.

Possible features:

- interaction frequency
- session frequency
- average session duration
- metric proportions
- content-category interaction frequency

Do NOT use private content.

Implement an online/lightweight clustering approach.

Possible initial implementation:

- MiniBatchKMeans or another suitable streaming-compatible approach

If a custom streaming clustering algorithm is implemented, document its assumptions.

Output:

cluster_id
cluster size
cluster statistics
cluster engagement metrics

STOP.

------------------------------------------------------------
PHASE 15 — SEGMENT-LEVEL DEGRADATION
------------------------------------------------------------

Goal:

Determine whether specific clusters are disproportionately affected.

For each segment:

expected engagement
observed engagement
degradation
Z-score
significance
contribution to global degradation

Example:

Heavy users: -31%
Video-focused: -27%
Casual users: -4%

The system should identify:

- most affected segment
- least affected segment
- segment contribution
- statistically significant segments

STOP.

------------------------------------------------------------
PHASE 16 — CAUSAL ANALYSIS EXTENSION
------------------------------------------------------------

Goal:

Avoid incorrectly treating correlation as causation.

Implement an optional control-stream approach.

Where appropriate, implement Difference-in-Differences:

Treatment:
affected population

Control:
less-affected comparison population

Conceptually:

DiD =
(Post_Treatment - Pre_Treatment)
-
(Post_Control - Pre_Control)

Clearly state assumptions.

Do NOT claim causal proof when assumptions are violated.

Create a report section:

"Causal interpretation and limitations"

STOP.

------------------------------------------------------------
PHASE 17 — MACHINE LEARNING EXTENSION
------------------------------------------------------------

Goal:

Introduce ML only where it provides measurable value.

Implement:

ML Engagement Prediction

Features may include:

- hour
- day of week
- historical engagement
- recent engagement
- user segment
- content category
- session statistics
- policy state where appropriate

Start with:

XGBoost

Compare against:

- exponential smoothing
- ARIMA if implemented

Prediction target:

expected future engagement

Evaluate:

- MAE
- RMSE
- MAPE where appropriate

Then integrate:

ML expected engagement
        ↓
CAGED statistical detector

Do NOT replace statistical validation with ML.

The research question should be:

"Does ML-based expected-engagement prediction improve degradation detection compared with the statistical baseline?"

STOP.

------------------------------------------------------------
PHASE 18 — ALERT ENGINE
------------------------------------------------------------

Goal:

Create meaningful alerts.

Alert should contain:

- alert ID
- policy ID
- timestamp
- affected metrics
- expected values
- observed values
- degradation percentages
- Z-scores
- composite score
- affected segments
- severity
- confidence/significance information
- causal-analysis status where available

Severity levels:

INFO
WARNING
CRITICAL

Avoid excessive alerts.

Implement alert deduplication/cooldown.

STOP.

------------------------------------------------------------
PHASE 19 — REPORT ENGINE
------------------------------------------------------------

Goal:

Generate human-readable policy impact reports.

Report structure:

CAGED POLICY IMPACT REPORT

Policy:
P-004

Policy time:
10:00

Analysis window:
...

Global engagement:
...

Metric analysis:
...

Statistical significance:
...

Composite degradation:
...

Affected segments:
...

Potential confounders:
...

Causal interpretation:
...

Privacy:
No private content processed

Generate:

- JSON report
- HTML report
- optionally PDF later

Reports must be reproducible from stored experiment results.

STOP.

------------------------------------------------------------
PHASE 20 — BACKEND API
------------------------------------------------------------

Goal:

Expose CAGED through REST APIs.

Implement endpoints such as:

GET /health

GET /metrics

GET /metrics/{metric}

GET /baseline/{metric}

GET /policies

POST /policies

GET /policies/{policy_id}

GET /alerts

GET /alerts/{alert_id}

GET /segments

GET /reports

GET /reports/{report_id}

POST /simulation/start

POST /simulation/stop

GET /simulation/status

POST /experiments/run

GET /experiments/{experiment_id}

Use Pydantic schemas.

Add validation.

Add API documentation.

STOP.

------------------------------------------------------------
PHASE 21 — DATABASE
------------------------------------------------------------

Goal:

Persist important application state.

Tables/entities:

users or pseudonymous user profiles if necessary
engagement_metrics
policy_events
baseline_snapshots
alerts
segments
reports
experiments

Do NOT store private content.

Use migrations.

Do not persist every raw event indefinitely unless explicitly required.

Prefer:

raw event stream
    ↓
processing
    ↓
aggregated state
    ↓
persistent analytical results

STOP.

------------------------------------------------------------
PHASE 22 — REAL-TIME DASHBOARD
------------------------------------------------------------

Goal:

Build the monitoring UI.

Dashboard should display:

1. System status
2. Current engagement
3. Expected engagement
4. Actual engagement
5. Degradation percentage
6. Z-score
7. Composite degradation score
8. Policy timeline
9. Alerts
10. Affected segments
11. Metric comparison charts
12. Historical trend
13. Experiment controls
14. Report viewer

Important visualization:

Expected vs Actual

```text
Engagement
   |
   |      Expected ─────────────
   |                   \
   |                    \
   | Actual              \
   | ────────────────\____
   |
   +--------------------------> Time
                     ↑
                Policy Change
````

Do not make the dashboard purely decorative.

Every visualization must correspond to an analytical result.

STOP.

---

## PHASE 23 — REAL-TIME UPDATE SYSTEM

Goal:

Make the dashboard update as events are processed.

Implement:

* polling or WebSocket/SSE
* real-time metric updates
* alert updates
* policy timeline updates

Prefer WebSocket/SSE only if justified.

Ensure frontend handles:

* connection loss
* reconnection
* stale data
* loading
* error states

STOP.

---

## PHASE 24 — EXPERIMENT FRAMEWORK

Goal:

Make scientific evaluation reproducible.

Create scenario definitions.

Required scenarios:

1. No policy change
2. Small degradation
3. Large degradation
4. Segment-specific degradation
5. Seasonal fluctuation
6. External event/confounder
7. Multiple policy changes
8. Gradual degradation
9. Sudden degradation
10. Metric-specific degradation

Every scenario must define:

* seed
* users
* duration
* event rate
* baseline behavior
* policy time
* degradation magnitude
* affected segment
* ground truth

STOP.

---

## PHASE 25 — EVALUATION

Goal:

Quantitatively evaluate CAGED.

Calculate:

Precision
Recall
F1
False Positive Rate
False Negative Rate
Detection Delay
MAE
RMSE
Memory Usage
Throughput
Sketch Relative Error
Segment Localization Accuracy

Compare:

A. Basic statistical baseline
B. CAGED
C. CAGED + ML

Produce tables.

Example:

Method | Precision | Recall | F1 | Delay | Memory

Also evaluate:

Exact aggregation
vs
Count-Min Sketch

and:

Traditional baseline
vs
ML baseline

STOP.

---

## PHASE 26 — STRESS TESTING

Goal:

Determine scalability.

Test event rates such as:

1,000 events/sec
10,000 events/sec
100,000 events/sec

where hardware permits.

Measure:

* events/sec
* CPU
* RAM
* latency
* detection delay
* sketch error
* cluster-processing time

Do not fabricate benchmark numbers.

Only report measured results.

STOP.

---

## PHASE 27 — SECURITY + PRIVACY AUDIT

Audit:

* sensitive data handling
* API validation
* secrets
* authentication assumptions
* authorization assumptions
* logs
* database contents
* frontend exposure
* pseudonymization
* data retention

Verify that:

private messages
private content
passwords
unnecessary PII

are never passed into CAGED analytical modules.

Create:

docs/security.md
docs/privacy.md

STOP.

---

## PHASE 28 — TESTING

Create a complete test suite.

Unit tests:

* event validation
* preprocessing
* metric aggregation
* Count-Min Sketch
* HyperLogLog
* baseline
* Z-score
* multi-metric score
* clustering
* ML prediction
* alert generation

Integration tests:

event
→ ingestion
→ aggregation
→ baseline
→ policy
→ detection
→ segmentation
→ report

End-to-end test:

simulation
→ backend
→ dashboard
→ alert
→ report

Target strong coverage of core statistical modules.

Do not chase coverage numbers without meaningful tests.

STOP.

---

## PHASE 29 — DOCKERIZATION

Create:

Dockerfile
docker-compose.yml

Services may include:

backend
frontend
postgres

Only add Kafka if the final architecture requires it.

Ensure:

docker compose up

can run the complete system.

STOP.

---

## PHASE 30 — FINAL INTEGRATION

Integrate all components.

Run:

Synthetic platform
↓
Event stream
↓
CAGED
↓
Policy change
↓
Detection
↓
Segmentation
↓
Report
↓
Dashboard

Verify that the entire pipeline works.

Run all tests.

Fix integration bugs.

STOP.

---

## PHASE 31 — FINAL DOCUMENTATION

Generate/update:

README.md

docs/
architecture.md
methodology.md
statistical-methods.md
streaming.md
sketches.md
segmentation.md
ml-extension.md
privacy.md
security.md
experiments.md
evaluation.md
limitations.md
future-work.md
api.md

README must explain:

* what CAGED is
* why it exists
* architecture
* installation
* running the simulator
* starting backend
* starting frontend
* running experiments
* interpreting results

STOP.

============================================================

# 9. STATISTICAL DEFINITIONS

============================================================

The implementation must preserve the following conceptual definitions.

Expected engagement:

E_t = μ_t + η_t

Degradation:

D = μ - E

Normalized deviation:

Z = D / σ

Multi-metric score:

S = Σ max(Z_k, 0)^2

Detection:

if S >= Θ:
degradation detected

Do not blindly use these equations without handling:

* zero variance
* insufficient observations
* missing observations
* numerical stability
* estimation uncertainty

Document every assumption.

============================================================

# 10. DATA FLOW

============================================================

The canonical data flow must be:

Raw synthetic activity
↓
Privacy filtering
↓
Validated EngagementEvent
↓
Streaming ingestion
↓
Metric extraction
↓
Exact/sketch aggregation
↓
Baseline learning
↓
Policy trigger
↓
Baseline freeze
↓
Post-policy observation
↓
Expected vs actual
↓
Statistical deviation
↓
Multi-metric score
↓
Segment analysis
↓
Optional causal analysis
↓
Optional ML prediction
↓
Alert
↓
Report
↓
Dashboard

============================================================

# 11. IMPORTANT DISTINCTION: DETECTION VS CAUSATION

============================================================

Never claim:

"Engagement decreased after policy, therefore the policy caused it."

Instead report:

"Engagement degradation was detected following the policy adjustment."

If causal assumptions and a suitable control strategy are available:

"Evidence is consistent with a policy-associated effect under the stated assumptions."

Clearly distinguish:

Correlation
Temporal association
Statistical significance
Causal inference

============================================================

# 12. IMPORTANT DISTINCTION: CAGED VS SIMULATOR

============================================================

The Synthetic Social Platform is only the experimental environment.

CAGED is the analytical framework.

The dashboard is the application interface.

Use these terms consistently.

Do not call the simulator "CAGED."

Do not describe the entire project as "a fake YouTube."

Instead:

"CAGED is evaluated using a synthetic social-platform event environment."

============================================================

# 13. MACHINE LEARNING BOUNDARY

============================================================

The project is fundamentally statistical.

ML is an extension.

The ML component must answer:

"Can machine learning improve expected engagement prediction and consequently improve degradation detection?"

It must NOT be inserted arbitrarily.

Compare:

Statistical baseline
vs
ML prediction

Then compare:

CAGED statistical detector
vs
CAGED + ML prediction

Use measurable evaluation.

============================================================

# 14. PRIVACY BOUNDARY

============================================================

CAGED should only process the minimum data required.

Allowed examples:

likes
comments
shares
clicks
sessions
session duration
views
content category
time
pseudonymous behavioral segment

Disallowed:

message contents
private conversations
passwords
private documents
private media
contact lists
unnecessary PII

Do not put private content into logs, databases, ML features, statistical features, or API responses.

============================================================

# 15. FAILURE HANDLING

============================================================

The system must gracefully handle:

* malformed events
* missing timestamps
* invalid metric
* duplicate events
* clock anomalies
* empty windows
* insufficient baseline data
* zero variance
* sketch initialization failure
* clustering failure
* ML prediction failure
* database failure
* stream interruption

An ML failure must NOT stop the core statistical CAGED detector.

The statistical engine must remain functional independently.

============================================================

# 16. CONFIGURATION

============================================================

Do not hard-code experimental parameters.

Use configuration for:

EVENT_RATE
WINDOW_SIZE
BASELINE_ALPHA
DETECTION_THRESHOLD
TARGET_FALSE_ALARM_RATE
CMS_WIDTH
CMS_DEPTH
HLL_PRECISION
CLUSTER_COUNT
ML_ENABLED
POLICY_TIME
SIMULATION_SEED

Provide:

.env.example

and a typed configuration class.

============================================================

# 17. LOGGING

============================================================

Use structured logging.

Log:

* event-processing errors
* policy events
* baseline initialization
* baseline freeze
* detection events
* alerts
* experiment lifecycle
* system failures

Never log:

* private content
* secrets
* passwords
* unnecessary personal data

============================================================

# 18. CODE QUALITY

============================================================

For every implementation:

* type hints
* docstrings for public APIs
* meaningful names
* small functions
* testable modules
* no giant files
* no duplicated logic
* no unnecessary abstraction
* no dead code
* no commented-out junk
* no debug print statements in production code

Use dependency injection where it improves testability.

============================================================

# 19. REQUIRED VALIDATION AFTER EACH PHASE

============================================================

At the end of every phase provide:

## Implemented

List actual components created.

## Files Changed

List files.

## Tests

List tests executed and results.

## Validation

Explain what was verified.

## Known Limitations

Only real limitations.

## Next Phase

State the next phase but DO NOT implement it.

Then STOP.

============================================================

# 20. IMPORTANT ANTI-HALLUCINATION RULE

============================================================

Never claim that something works without running it.

Never claim a benchmark result without measuring it.

Never fabricate:

* accuracy
* latency
* memory
* throughput
* statistical significance
* ML performance

If something cannot be tested in the current environment, say so.

============================================================

# 21. IMPORTANT IMPLEMENTATION RULE

============================================================

Before implementing any algorithm:

1. explain its role in CAGED
2. define its inputs
3. define its outputs
4. define mathematical assumptions
5. implement
6. test against known/simple cases
7. integrate

Especially apply this to:

* Count-Min Sketch
* HyperLogLog
* exponential smoothing
* ARIMA
* Z-score detection
* composite score
* clustering
* Difference-in-Differences
* XGBoost

============================================================

# 22. FIRST ACTION

============================================================

Start ONLY with PHASE 0.

Do NOT implement Phase 1 yet.

First inspect the existing repository.

Determine:

* current architecture
* existing backend
* existing frontend
* dependencies
* database
* reusable modules
* conflicting architecture
* missing components

Then produce:

1. repository audit
2. proposed CAGED architecture
3. implementation plan
4. Phase 0 documentation changes

After Phase 0 is complete and validated:

STOP and wait for:

"Continue to Phase 1"

============================================================

# FINAL PRINCIPLE

============================================================

The final project should demonstrate:

"Continuous privacy-safe engagement monitoring
→ adaptive statistical baseline
→ policy-triggered baseline freezing
→ statistically validated degradation detection
→ multi-metric analysis
→ affected-user segmentation
→ optional causal analysis
→ optional ML prediction
→ interpretable alerts and reports."

Build it incrementally.
Do not skip validation.
Do not fabricate results.
Do not process private user content.
Do not confuse correlation with causation.
Do not add machine learning unless it provides measurable value.

````

## How to use this

Paste the entire prompt into your coding agent **at the root of the project repository**.

The agent should initially do only:

> **Phase 0 — Repository Audit + Technical Design**

Then you give it:

```text
Continue to Phase 1.
````

After Phase 1:

```text
Continue to Phase 2.
```

And so on.

### One change I strongly recommend

Do **not** tell the agent:

> "Build the whole CAGED project."

That encourages it to generate a large amount of interconnected code before the statistical core has been validated.

The phase sequence above deliberately makes the dependency chain:

```text
Foundation
   ↓
Data model
   ↓
Simulator
   ↓
Streaming
   ↓
Metrics
   ↓
Sketches
   ↓
Baseline
   ↓
Policy
   ↓
Statistical detector
   ↓
Segmentation
   ↓
Causal analysis
   ↓
ML
   ↓
Alerts
   ↓
Reports
   ↓
API
   ↓
Dashboard
   ↓
Evaluation
```

