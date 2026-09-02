# CAGED — Privacy Architecture & Data Minimization Specification

## 1. Core Principle

> **"Measure behavior, not private content."**

CAGED is engineered ground-up around **Privacy by Design**. The framework continuously monitors privacy-safe behavioral engagement events across high-volume streams without ever acquiring, inspecting, or processing private user content, personal communications, or sensitive personally identifiable information (PII).

---

## 2. Data Minimization Principles

1. **No Private Content Collection**:
   CAGED explicitly rejects any event fields containing private messages, text content, documents, photos, videos, or audio recordings.
2. **Pseudonymization at Source**:
   User identity is never ingested or stored as raw user names, email addresses, phone numbers, or account IDs. Every user is represented solely by a non-reversible SHA-256 hash (`user_hash`) generated with a secret salt.
3. **Coarse Behavioral Metadata**:
   Segment metadata is restricted strictly to coarse, non-identifying behavioral counts and top-level categories (e.g. content topic = "education", session count = 5).
4. **Zero Persistent PII Storage**:
   Downstream statistical engines operate entirely on numerical aggregations, sketch structures (Count-Min Sketch, HyperLogLog), and time-series totals.

---

## 3. Pseudonymization Strategy

Pseudonymization converts raw user identifiers into deterministic, un-linkable 64-character SHA-256 hashes using the HMAC/Salted formula:

$$\text{user\_hash} = \text{SHA256}(\text{raw\_user\_id} \mathbin{\Vert} \text{HASH\_SALT})$$

- **Irreversibility**: It is computationally infeasible to reconstruct the original raw identity from the `user_hash`.
- **Consistency**: The same user activity can be tracked across continuous time windows without exposing individual identity.
- **Strict Validation**: The `EngagementEvent` parser automatically rejects any `user_hash` containing email symbols (`@`), phone prefixes (`+`), or whitespace.

---

## 4. Forbidden Private Fields

The `PrivacySanitizer` automatically inspects incoming event structures and rejects any payload containing the following forbidden fields:

| Category | Forbidden Attributes |
| :--- | :--- |
| **Private Messages** | `message_content`, `private_message`, `chat_history` |
| **User Credentials** | `password`, `secret`, `biometric_data` |
| **Private Media** | `private_photo`, `private_video`, `private_document` |
| **Personal Identifiers (PII)** | `email`, `phone`, `phone_number`, `real_name`, `full_name`, `ssn`, `social_security_number` |
| **Social Data** | `contact_list` |
| **Exact Geolocation** | `exact_location`, `gps_coordinates`, `street_address` |

If any of these keys are present anywhere in the payload (including nested dictionaries or metadata lists), the event is immediately flagged with a `PrivacyViolationException` and discarded before reaching analytical modules.

---

## 5. Metric Collection Justification

Every metric collected by CAGED is necessary and sufficient for measuring platform-level engagement health:

| Metric Type | Data Type | Purpose & Necessity | Privacy Justification |
| :--- | :--- | :--- | :--- |
| `like` | `float` (1.0) | Measures binary positive user affinity | Aggregated count; no content context stored |
| `comment` | `float` (1.0) | Measures user interaction intensity | Counts comment creation count only; zero comment text collected |
| `share` | `float` (1.0) | Tracks virality and content propagation | Tracks distribution rate; recipient and content details omitted |
| `click` | `float` (1.0) | Measures navigation and link interaction | Binary interaction signal; no URL parameters logged |
| `session` | `float` (1.0) | Measures active platform user visits | Simple counter of session initialization |
| `session_duration` | `float` (seconds) | Measures user retention and time spent | Numerical duration in seconds; no activity trace captured |
| `view` | `float` (1.0) | Measures impression volume | Counter of content impressions |

---

## 6. Summary Compliance Checklist

- [x] No private message content processed.
- [x] No credentials or PII stored.
- [x] Pseudonymization enforced via SHA-256 + secret salt.
- [x] Forbidden fields rejected automatically at ingestion boundary.
- [x] Statistical aggregators isolate metrics from identity data.
