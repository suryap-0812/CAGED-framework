# CAGED — Complete Project Document

Below is a **complete project document** for the CAGED framework, structured so that you can use it as the foundation for your **Data Science project report, implementation plan, presentation, and viva**.

I am keeping the core methodology aligned with your uploaded CAGED document. Where I add the **privacy layer, ML extension, simulator, and practical implementation choices**, I explicitly treat them as proposed implementation extensions rather than claiming they are already part of the original framework.

---

# 1. Project Title

## **CAGED**

### **Causal Analysis for Guaranteed Engagement Degradation**

**Project Theme:** Real-Time Statistical Analysis and Streaming Data Science

**Project Type:** Algorithmic / Statistical Analytics Framework implemented as a real-time monitoring system

---

# 2. Abstract

Social platforms continuously modify policies related to content moderation, recommendation systems, privacy, and community standards. Such changes can alter user engagement, but distinguishing genuine policy-related degradation from normal fluctuations, seasonal patterns, or external events is challenging. Traditional approaches generally rely on offline analysis of historical data and may not scale effectively to high-volume engagement streams.

This project proposes **CAGED (Causal Analysis for Guaranteed Engagement Degradation)**, a real-time statistical framework designed to detect and localize engagement degradation following platform policy adjustments. CAGED continuously processes engagement events, extracts multiple engagement metrics, and uses memory-efficient sketch-based structures such as Count-Min Sketch and HyperLogLog for scalable aggregation. During the pre-policy period, an adaptive baseline is learned using techniques such as exponential smoothing or lightweight ARIMA. When a policy change occurs, the pre-policy baseline is frozen and used as a counterfactual reference for subsequent analysis. Incoming post-policy engagement is then compared against the expected baseline using statistical deviation measures and multi-metric detection.

When statistically significant degradation is identified, CAGED performs streaming user segmentation to determine which user communities or content categories are disproportionately affected. The system then produces alerts and analytical reports describing the magnitude, statistical significance, and affected segments. A privacy-preserving implementation can restrict the system to behavioral telemetry and aggregate statistics rather than private user content.

The resulting system provides a scalable approach for real-time monitoring of engagement changes while combining streaming analytics, statistical validation, segmentation, and optional machine-learning extensions.

---

# 3. Problem Statement

Social platforms generate enormous volumes of engagement events such as:

* likes
* comments
* clicks
* shares
* posts
* sessions
* session duration
* content interactions

When a platform introduces a policy change, engagement may increase, decrease, or change differently across user groups.

The problem is:

> **How can we continuously determine whether a change in engagement following a policy adjustment represents statistically significant degradation rather than ordinary behavioral variation, while efficiently processing high-volume streaming data?**

Existing approaches have several limitations.

They often:

* analyze data retrospectively;
* operate on fixed historical datasets;
* focus on only a few engagement metrics;
* do not adequately address streaming scalability;
* treat the user population as homogeneous;
* have limited causal/confounder control.

These gaps are identified in the source document. 

---

# 4. Proposed Solution

CAGED addresses the problem through a unified streaming pipeline:

```text
                 USER ENGAGEMENT EVENTS
                          │
                          ▼
              Data Ingestion & Cleaning
                          │
                          ▼
                 Metric Extraction
                          │
                          ▼
               Sketch-Based Aggregation
                          │
                          ▼
               Adaptive Baseline Model
                          │
                          ▼
                  Policy Change Event
                          │
                          ▼
               Freeze Pre-Policy Baseline
                          │
                          ▼
             Post-Policy Statistical Test
                          │
                          ▼
                Multi-Metric Detection
                          │
                          ▼
                  Global Degradation?
                     /          \
                   No            Yes
                   │              │
                   │              ▼
                   │       User Segmentation
                   │              │
                   │              ▼
                   │       Segment-Level Tests
                   │              │
                   └──────────────┤
                                  ▼
                          Alert / Report
```

This modular architecture is directly based on the proposed CAGED workflow. 

---

# 5. Real-World Interpretation

CAGED is **not a replacement for YouTube, Netflix, Instagram, etc.**

Instead, imagine that a platform has an internal monitoring system:

```text
                  YouTube-like Platform
                          │
                   User activity
                          │
                          ▼
                    Event Stream
                          │
                          ▼
                       CAGED
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
         Statistics    Segments      Alerts
             │            │            │
             └────────────┼────────────┘
                          ▼
                    Analyst Dashboard
```

For the college implementation, you would create a **synthetic social-platform event generator** instead of attempting to build a complete YouTube clone.

---

# 6. Objectives

## Primary Objective

Develop a real-time statistical framework capable of detecting engagement degradation after policy changes.

## Secondary Objectives

1. Process engagement events continuously.
2. Monitor multiple engagement metrics simultaneously.
3. Maintain an adaptive pre-policy baseline.
4. Detect statistically abnormal deviations.
5. Reduce memory requirements through sketch-based aggregation.
6. Identify affected user segments.
7. Control false alarms.
8. Generate interpretable alerts and reports.
9. Preserve user privacy through data minimization.
10. Evaluate the framework using controlled synthetic experiments.

---

# 7. Engagement Data

CAGED should focus on **behavioral telemetry**, not private content.

## Recommended metrics

### Interaction metrics

```text
likes
comments
shares
clicks
posts
```

### Session metrics

```text
session count
session duration
active sessions
returning sessions
```

### Content interaction metrics

```text
content views
watch/interactions duration
content-category interactions
```

The source document explicitly describes events such as clicks, likes, posts, sessions, comments, and session durations. 

---

# 8. Privacy-by-Design

This should be an **implementation-level addition** to the original framework.

CAGED should follow the principle:

> **Measure behavior, not private content.**

## Data CAGED should NOT process

```text
Private messages
Message contents
Passwords
Private documents
Private photos
Private videos
Contact lists
Exact personal location
Sensitive personal information
```

Instead, the system should receive minimized telemetry such as:

```json
{
    "user_hash": "a81f...",
    "metric": "like",
    "timestamp": "10:42:13",
    "content_category": "education"
}
```

Or, where individual-level information is unnecessary:

```json
{
    "timestamp": "10:42",
    "metric": "likes",
    "segment": "heavy_users",
    "count": 1842
}
```

This means the analytical engine works primarily with:

```text
Counts
Rates
Durations
Aggregates
Statistical summaries
Pseudonymous identifiers where necessary
```

rather than private user content.

---

# 9. System Architecture

## 9.1 Data Ingestion

The system receives a continuous stream:

```text
Event 1
Event 2
Event 3
Event 4
...
Event N
```

Each event can contain:

```text
user_id
metric_id
increment/value
timestamp
```

The CAGED pseudocode defines the input in essentially this form. 

---

# 10. Data Preprocessing

Incoming events are cleaned before analysis.

Operations include:

### Deduplication

Remove duplicate events.

### Noise filtering

Remove invalid or suspicious events.

### Bot filtering

The source design proposes simple heuristics for detecting bot-generated events, such as abnormal timing patterns and authority lists. 

### Standardization

Convert events into a common structure.

```text
Raw Event
    ↓
Validate
    ↓
Deduplicate
    ↓
Filter noise/bots
    ↓
Standardized Event
```

---

# 11. Metric Extraction

Each event is mapped to one or more quantitative metrics.

For example:

```text
LIKE event
   ↓
likes += 1
```

```text
COMMENT event
   ↓
comments += 1
```

```text
SESSION event
   ↓
session_count += 1
session_duration += duration
```

The source document defines this as mapping each event to quantitative features and maintaining fixed engagement metric streams. 

---

# 12. Sketch-Based Aggregation

This is one of the key technical components.

Instead of storing every event individually, CAGED can use:

### Count-Min Sketch

Used for approximate frequency/count estimation.

```text
Likes
Posts
Comments
Clicks
```

### HyperLogLog

Used when approximate unique-count/cardinality estimation is required.

The source explicitly proposes Count-Min Sketch and HyperLogLog for high-volume aggregation. 

---

# 13. Why Sketches?

Imagine:

```text
1,000,000,000 events
```

Storing and repeatedly processing every raw event is expensive.

CAGED instead maintains compact summaries:

```text
1 billion events
       ↓
Compact sketches
       ↓
Approximate statistics
```

The trade-off is:

> **Small controlled approximation error in exchange for substantially lower memory requirements.**

The source describes this sublinear-space objective and the associated accuracy trade-off. 

---

# 14. Adaptive Baseline

This is arguably the most important statistical component.

Before the policy change, CAGED learns:

> **What does normal engagement look like?**

For example:

```text
09:00 → 98,000
09:15 → 101,000
09:30 → 99,000
09:45 → 102,000
```

The system estimates the expected engagement:

$$
E_{k,t} = \mu_{k,t} + \eta_{k,t}
$$

where:

* \(E_{k,t}\) = engagement metric
* \(\mu_{k,t}\) = expected baseline
* \(\eta_{k,t}\) = noise

The source proposes exponential smoothing or lightweight ARIMA for this purpose. 

---

# 15. Policy Event

At some point:

```text
T₀ = Policy Change Time
```

Example:

```text
10:00 AM
↓
Recommendation policy changed
```

CAGED receives this as an external trigger.

At \(T_0\), it freezes the pre-policy baseline:

```text
Pre-policy baseline
        ↓
      FREEZE
        ↓
Counterfactual reference
```

The source explicitly describes the frozen baseline as a counterfactual model of expected engagement without the policy change. 

---

# 16. Post-Policy Monitoring

After \(T_0\), new events continue arriving.

Suppose:

$$
\mu = 100,000
$$

but:

$$
E = 80,000
$$

Then:

$$
D = \mu-E
$$

$$
D = 20,000
$$

This is the observed engagement drop relative to the frozen baseline.

---

# 17. Statistical Deviation

CAGED normalizes the drop:

$$
Z=\frac{D}{\sigma}
$$

where:

* \(D\) = observed degradation
* \(\sigma\) = estimated baseline standard deviation

For example:

$$
D=20,000
$$

$$
\sigma=5,000
$$

therefore:

$$
Z=4
$$

The source describes this normalized Z-score formulation and threshold-based detection. 

---

# 18. Multi-Metric Detection

CAGED does not rely on one metric.

Suppose:

```text
Likes       Z = 3.1
Comments    Z = 2.7
Shares      Z = 3.4
Sessions    Z = 2.9
```

A composite degradation score can be calculated:

$$
S=\sum_k \max(Z_k,0)^2
$$

If:

$$
S\geq\Theta
$$

the system generates a global degradation alert.

This is the mechanism specified in the CAGED pseudocode. 

---

# 19. False-Alarm Control

A major requirement is:

> **Don't report every small fluctuation as degradation.**

The threshold \(\Theta\) should be calibrated using the desired false-alarm rate.

Possible approaches described in the source include:

* bootstrapping pre-policy noise;
* concentration inequalities;
* sketch-error bounds;
* multiple-comparison corrections.



---

# 20. User Segmentation

Suppose CAGED detects:

```text
Global engagement ↓ 20%
```

It then asks:

> **Which users or communities are responsible for the decline?**

Streaming clustering can create groups such as:

```text
Cluster 1 → Casual users
Cluster 2 → Heavy users
Cluster 3 → Video-focused users
Cluster 4 → Low-frequency users
```

The source proposes lightweight streaming clustering such as streaming k-centers or micro-clusters. 

---

# 21. Segment-Level Detection

Suppose:

```text
Casual users      → -4%
Heavy users       → -31%
Video users       → -27%
Low-frequency     → -2%
```

CAGED can identify:

> **Heavy-user and video-oriented segments experienced the strongest statistically significant degradation.**

The source specifically describes cluster-level aggregate testing and localization of affected communities/content categories. 

---

# 22. Causal Interpretation

This needs careful wording.

CAGED should **not** automatically claim:

> "The policy caused the decline."

Instead:

```text
Policy change
     ↓
Baseline frozen
     ↓
Post-policy deviation
     ↓
Statistical validation
     ↓
Possible policy-associated degradation
```

If there is a strong pre-existing trend or another simultaneous event, CAGED can incorporate a control stream and Difference-in-Differences-style analysis. 

Therefore:

> **CAGED improves causal attribution but does not magically prove causality from temporal correlation alone.**

This is an important limitation to preserve in the final project.

---

# 23. Optional Machine Learning Extension

The original CAGED design is primarily **statistical/streaming**, not a conventional ML system.

However, we can introduce an ML module.

## Proposed ML Feature: Engagement Prediction

Instead of relying only on:

```text
Exponential Smoothing / ARIMA
```

we can add:

```text
Historical features
       ↓
ML model
       ↓
Expected engagement
       ↓
CAGED statistical detector
```

For example:

```text
Time
Day
Historical engagement
User segment
Content category
Recent interactions
Session statistics
```

can be used to predict:

$$
\hat{E}_{t+1}
$$

Then CAGED evaluates:

$$
Actual-\hat{E}_{t+1}
$$

This creates a **hybrid ML + statistical framework**.

### Recommended first model

For a college implementation:

> **XGBoost**

is a practical starting point for structured/tabular engagement data.

Do not add ML merely for the label "Data Science." It should be evaluated against the original statistical baseline.

---

# 24. Experimental Environment

You should build a:

## **Synthetic Social Platform Event Generator**

It produces realistic engagement streams.

For example:

```text
User 101 → like
User 204 → comment
User 302 → session
User 101 → share
User 782 → like
...
```

Then simulate:

```text
NORMAL PERIOD
      ↓
POLICY CHANGE
      ↓
ENGAGEMENT CHANGE
```

This lets you know the **ground truth**.

For example:

```text
Actual simulated degradation = 25%
```

Then you test whether CAGED detects approximately that change.

The source itself recognizes simulated datasets as a limitation in prior work, so your report should clearly state that your experimental environment is synthetic and discuss generalization accordingly. 

---

# 25. Experimental Scenarios

You should test at least these scenarios.

## Scenario 1 — No Policy Change

```text
Normal fluctuations
        ↓
No alert
```

Purpose:

> Measure false-positive rate.

---

## Scenario 2 — Small Degradation

```text
Policy
 ↓
5% engagement drop
```

Expected:

```text
No significant alert
```

if it falls within normal variation.

---

## Scenario 3 — Large Degradation

```text
Policy
 ↓
30% engagement drop
```

Expected:

```text
Global degradation detected
```

---

## Scenario 4 — Segment-Specific Degradation

```text
Overall → -10%

Heavy users → -35%
Casual users → -3%
```

Expected:

> Heavy-user segment identified.

---

## Scenario 5 — Natural Seasonal Change

```text
Weekend
 ↓
Engagement naturally changes
```

Expected:

> CAGED should avoid incorrectly attributing normal seasonality to a policy event.

The adaptive baseline is intended to account for trends and seasonality. 

---

## Scenario 6 — External Event

```text
Policy change
+
External event
```

Expected:

> Demonstrate the limitation of simple attribution and, where implemented, compare performance with a control stream.

---

# 26. Dashboard

The final system can have a web dashboard.

## Dashboard sections

### Current status

```text
Policy: P-004
Policy time: 10:00 AM

Status:
🔴 SIGNIFICANT DEGRADATION
```

### Metrics

```text
Likes       ↓ 18%
Comments    ↓ 24%
Shares      ↓ 21%
Sessions    ↓ 15%
```

### Statistical indicators

```text
Z-score
Composite degradation score
Threshold
Confidence/significance information
```

### Segment analysis

```text
Heavy users       ↓ 31%
Video users       ↓ 27%
Casual users      ↓  4%
```

### Policy timeline

```text
09:00 ───── 10:00 ───── 11:00 ───── 12:00
             ↑
        Policy Change
```

---

# 27. Example Generated Report

```text
================================================
             CAGED POLICY IMPACT REPORT
================================================

Policy ID:
P-004

Policy Change:
10:00 AM

Analysis Window:
10:00 AM – 12:00 PM

------------------------------------------------
GLOBAL ENGAGEMENT
------------------------------------------------

Likes:
Expected     : 100,000
Observed     : 82,000
Degradation : 18%

Comments:
Expected     : 30,000
Observed     : 22,500
Degradation : 25%

Shares:
Expected     : 15,000
Observed     : 11,800
Degradation : 21%

------------------------------------------------
STATISTICAL ANALYSIS
------------------------------------------------

Composite Score : 34.7
Threshold        : 20.0

Status:
SIGNIFICANT DEGRADATION DETECTED

------------------------------------------------
AFFECTED SEGMENTS
------------------------------------------------

Heavy Users     : -31%
Video Users     : -27%
Casual Users    : -4%

------------------------------------------------
PRIVACY
------------------------------------------------

Private content accessed: NO
Raw private communications processed: NO

================================================
```

---

# 28. Technology Stack

A practical implementation could use:

## Backend

**Python**

Because the project is heavily statistical/data-oriented.

Libraries:

```text
NumPy
Pandas
SciPy
Statsmodels
Scikit-learn
XGBoost        ← optional ML
```

## Streaming

For a college-scale prototype:

```text
Python async/event generator
```

For a more realistic architecture:

```text
Apache Kafka
```

## Statistical engine

```text
NumPy
SciPy
Statsmodels
```

## Sketches

Implement or use a suitable Python implementation of:

```text
Count-Min Sketch
HyperLogLog
```

## Clustering

```text
Scikit-learn
```

or a custom lightweight streaming clustering implementation.

## Backend API

```text
FastAPI
```

## Frontend

```text
React
```

## Visualization

```text
Plotly
```

or another charting library.

## Storage

```text
PostgreSQL
```

for configuration, policy events, experiment metadata, and reports.

---

# 29. Complete Software Architecture

```text
                         ┌───────────────────────┐
                         │ Synthetic Event       │
                         │ Generator              │
                         └───────────┬───────────┘
                                     │
                                     ▼
                              Event Stream
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ Data Ingestion        │
                         │ + Preprocessing       │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ Metric Extraction     │
                         └───────────┬───────────┘
                                     │
                                     ▼
                  ┌──────────────────────────────────┐
                  │      Streaming Aggregation       │
                  │                                  │
                  │ Count-Min Sketch                 │
                  │ HyperLogLog                     │
                  └────────────────┬─────────────────┘
                                   │
                    ┌──────────────┴───────────────┐
                    ▼                              ▼
          Adaptive Baseline                  User Clustering
          Exponential Smoothing              Streaming Clusters
          / ARIMA                                  │
                    │                              │
                    └──────────────┬───────────────┘
                                   ▼
                            Policy Trigger
                                   │
                                   ▼
                         Freeze Baseline
                                   │
                                   ▼
                       Statistical Detection
                                   │
                         ┌─────────┴─────────┐
                         ▼                   ▼
                  Multi-Metric          Optional ML
                    Analysis             Prediction
                         │                   │
                         └─────────┬─────────┘
                                   ▼
                           Degradation Score
                                   │
                                   ▼
                         Segment-Level Analysis
                                   │
                                   ▼
                         Alert + Report API
                                   │
                                   ▼
                             Web Dashboard
```

---

# 30. Core Algorithm

The simplified CAGED algorithm is:

```text
Initialize sketches
Initialize baseline statistics
Initialize streaming clusters

FOR every incoming event:

    validate event

    remove duplicates/noise

    identify metric

    update corresponding sketch

    update baseline statistics
        IF before policy time

    update user cluster

    IF policy time reached:
        freeze baseline

    IF after policy time:

        calculate observed engagement

        calculate degradation

        calculate normalized Z-score

        update composite degradation score

        IF composite score > threshold:

            trigger global alert

            FOR each user cluster:

                calculate cluster engagement

                calculate cluster degradation

                IF cluster threshold exceeded:

                    report affected cluster
```

This closely follows the pseudocode in the source document. 

---

# 31. Complexity Goal

One of the important motivations of CAGED is scalability.

The design aims for approximately:

```text
Per-event processing:
O(log K + d)
```

where:

* \(K\) = number of clusters
* \(d\) = sketch depth / related constant

The source describes constant-time sketch updates and logarithmic-style cluster assignment. 

Memory is intended to be substantially smaller than storing the entire raw event stream, using sketch structures and compact cluster representations. 

---

# 32. Evaluation Metrics

Your project should not only show a dashboard.

You need quantitative evaluation.

## Statistical detection

Measure:

### Precision

$$
Precision=\frac{TP}{TP+FP}
$$

### Recall

$$
Recall=\frac{TP}{TP+FN}
$$

### F1-score

$$
F1=2\frac{Precision\cdot Recall}{Precision+Recall}
$$

### False Positive Rate

Important because your framework is supposed to avoid unnecessary alerts.

### Detection Delay

```text
Actual policy impact
        ↓
Time until CAGED detects it
```

The source explicitly discusses the trade-off between detection delay and false alarms. 

---

# 33. Sketch Evaluation

Compare:

```text
Exact count
     vs
CMS estimate
```

Measure:

$$
Error = |Exact-Estimated|
$$

and:

$$
Relative\ Error =
\frac{|Exact-Estimated|}{Exact}
$$

This demonstrates whether your memory optimization is introducing acceptable error.

---

# 34. ML Evaluation

If you add the ML component, compare:

```text
Exponential Smoothing
        vs
ARIMA
        vs
XGBoost
```

using:

* MAE
* RMSE
* MAPE where appropriate

For example:

```text
                    RMSE

Exponential Smoothing  ███████████
ARIMA                  █████████
XGBoost                ███████
```

Then determine whether ML actually improves degradation detection.

---

# 35. Research Experiment

Your strongest experiment would be:

> **Does the proposed CAGED framework detect policy-induced engagement degradation more accurately and quickly than conventional offline statistical methods while using substantially less memory?**

Compare:

```text
Method A
Traditional statistical analysis

Method B
Time-series baseline

Method C
CAGED

Method D
CAGED + ML
```

Measure:

```text
Detection accuracy
False alarms
Detection delay
Memory usage
Processing throughput
Segment localization accuracy
Prediction error
```

This gives your project a real experimental component rather than simply producing a software demo.

---

# 36. Expected Output

CAGED should ultimately answer five questions:

### 1. Did engagement change?

```text
YES / NO
```

### 2. Was the change statistically significant?

```text
YES / NO
```

### 3. How large was the degradation?

```text
18.4%
```

### 4. Which metrics were affected?

```text
Likes
Comments
Sessions
Shares
```

### 5. Which user segments were affected?

```text
Heavy users
Video users
Specific communities
```

---

# 37. Limitations

Your project should openly acknowledge these.

### Causal limitation

A post-policy deviation does not automatically prove causation.

### Synthetic data limitation

Your college prototype will likely use generated/simulated data rather than proprietary platform data.

### Sketch approximation

Count-Min Sketch introduces bounded approximation error.

### Threshold sensitivity

Poor threshold selection can cause:

```text
Too sensitive → false alarms
Too insensitive → missed events
```

### Multiple policy changes

If several policies are introduced close together, attributing degradation to one policy becomes difficult. The source explicitly identifies this problem and proposes resetting or maintaining multiple baselines. 

### Segmentation cost

Streaming clustering can become expensive as the number of clusters/features increases. 

---

# 38. Future Enhancements

The system can later be extended with:

### Machine Learning

```text
ML engagement forecasting
ML impact prediction
Anomaly classification
```

### Causal inference

```text
Difference-in-Differences
Synthetic Control
Causal ML
```

### Advanced streaming

```text
Apache Kafka
Apache Flink
Apache Spark Streaming
```

### Privacy

```text
Differential Privacy
Federated Analytics
Privacy-preserving aggregation
```

### Explainability

Instead of:

> "Alert generated."

produce:

> "Engagement decreased 27% relative to the pre-policy baseline, primarily driven by heavy users and video-content interactions."

---

# 39. Final Project Classification

This is important for your college documentation.

### CAGED itself

> **Real-Time Statistical / Algorithmic Framework**

### Implementation

> **Real-Time Engagement Monitoring System**

### Experimental environment

> **Synthetic Social Platform Event Generator**

### Dashboard

> **Web-Based Analytics and Reporting Application**

### Data Science components

> **Streaming analytics + statistical modeling + time-series analysis + clustering**

### Optional ML component

> **ML-based engagement prediction/impact analysis**

So you should **not describe the entire project simply as an “ML application.”**

---

# 40. Final One-Minute Explanation

If your professor asks:

> **“Explain your project.”**

You can say:

> **“Our project is CAGED, a real-time statistical framework for detecting engagement degradation after social-platform policy changes. We simulate a social-platform event stream containing privacy-safe engagement telemetry such as likes, comments, clicks, sessions, and session duration. CAGED continuously processes these events using memory-efficient sketch structures and learns the platform's normal engagement behavior during the pre-policy period. When a policy change occurs, the pre-policy baseline is frozen and subsequent engagement is compared against the expected behavior using statistical deviation and multi-metric detection. If the deviation is statistically significant, CAGED identifies which metrics and user segments are most affected and generates an alert and analytical report. We can optionally add machine learning to improve expected-engagement prediction, but the core of CAGED is statistical and streaming analytics.”**

That is the cleanest description of the project as currently defined.

---

## The Core Idea in One Diagram

```text
                 ┌─────────────────────────┐
                 │   SOCIAL PLATFORM       │
                 │   USER ACTIVITY         │
                 └────────────┬────────────┘
                              │
                              ▼
                   ┌────────────────────┐
                   │ Privacy-Safe       │
                   │ Engagement Events  │
                   └─────────┬──────────┘
                             │
                             ▼
                   ┌────────────────────┐
                   │       CAGED        │
                   │                    │
                   │ Stream Processing  │
                   │       ↓            │
                   │ Sketch Aggregation │
                   │       ↓            │
                   │ Baseline Learning  │
                   │       ↓            │
                   │ Policy Detection   │
                   │       ↓            │
                   │ Statistical Test   │
                   │       ↓            │
                   │ Segmentation       │
                   └─────────┬──────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Engagement Impact    │
                  │ Report / Alert       │
                  └──────────────────────┘
```

**The key point:** the synthetic platform is only the **experimental data source**. **CAGED is the actual Data Science framework you are developing and evaluating.** The source document's core architecture, pseudocode, statistical formulation, segmentation, and scalability objectives support this interpretation.  
