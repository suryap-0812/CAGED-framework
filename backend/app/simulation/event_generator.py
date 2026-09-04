"""
Refactored Synthetic Social Platform Event Generator for CAGED.
Orchestrates ExperimentConfig, ContentCatalog, RecommendationEngine, and UserBehaviorModel.
Emits parallel Treatment & Control streams while preserving SUTVA no-interference and Ground-Truth Firewall Isolation.
"""

from datetime import datetime, timedelta, timezone
import math
import random
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.ingestion.models import EngagementEvent, MetricType
from app.preprocessing.validator import EventValidator
from app.simulation.content_catalog import ContentCatalog, ContentItem
from app.simulation.experiment_config import (
    ExperimentConfig,
    ExternalDisturbanceType,
    PolicyMechanism,
    PolicyParameters,
)
from app.simulation.recommender import RecommendationEngine
from app.simulation.user_behavior import UserBehaviorModel, UserBehaviorOutcome
from app.simulation.user_profile import (
    UserProfile,
    UserSegment,
    create_synthetic_user_profile,
)

# Backward-compatibility alias for legacy imports
EventGeneratorConfig = ExperimentConfig


class EventGenerator:
    """
    Core simulation engine orchestrating production-style recommendation mechanisms,
    user behavioral emergence, and treatment/control streams.
    """

    def __init__(
        self,
        config: Optional[ExperimentConfig] = None,
        timeline: Optional[Any] = None,  # Backward-compatibility parameter
        catalog: Optional[ContentCatalog] = None,
        recommender: Optional[RecommendationEngine] = None,
        behavior_model: Optional[UserBehaviorModel] = None,
    ):
        self.config = config or ExperimentConfig()
        self.timeline = timeline
        self.legacy_comment_suppression = 1.0
        
        # Legacy PolicyTimeline compatibility adapter
        if timeline and hasattr(timeline, "get_all_policy_events"):
            pol_events = timeline.get_all_policy_events()
            if pol_events:
                p_first = pol_events[0]
                self.config.t0 = p_first.timestamp
                if p_first.impact_factor < 1.0:
                    if hasattr(p_first, "target_metric") and p_first.target_metric == MetricType.COMMENT:
                        self.legacy_comment_suppression = p_first.impact_factor
                    else:
                        self.config.policy_mechanism = PolicyMechanism.ORIGINALITY_BOOST
                        self.config.policy_params.originality_weight_shift = (1.0 - p_first.impact_factor) * 3.0
                    self.legacy_policy_id = p_first.policy_id

        self.py_rng = random.Random(self.config.seed)
        self.np_rng = np.random.default_rng(self.config.seed)

        self.catalog = catalog or ContentCatalog(
            num_items=self.config.num_items,
            seed=self.config.seed,
        )
        self.recommender = recommender or RecommendationEngine()
        self.behavior_model = behavior_model or UserBehaviorModel(rng=self.py_rng)

        self.users: List[UserProfile] = []
        self.treatment_user_hashes: set[str] = set()
        self.control_user_hashes: set[str] = set()

        self._init_user_population()

    def _init_user_population(self) -> None:
        """Instantiates synthetic user population and assigns A/B treatment/control cohorts."""
        total_users = self.config.num_users
        categories = self.catalog.categories

        segments = [UserSegment.CASUAL, UserSegment.REGULAR, UserSegment.HEAVY, UserSegment.CONTENT_FOCUSED]
        segment_ratios = [0.50, 0.30, 0.10, 0.10]

        user_idx = 0
        for seg, ratio in zip(segments, segment_ratios):
            count = int(total_users * ratio)
            for _ in range(count):
                u = create_synthetic_user_profile(
                    user_index=user_idx,
                    segment=seg,
                    available_categories=categories,
                    rng=self.py_rng,
                )
                self.users.append(u)

                # Assign Treatment vs Control cohort based on treatment_ratio
                if self.py_rng.random() < self.config.treatment_ratio:
                    self.treatment_user_hashes.add(u.user_hash)
                else:
                    self.control_user_hashes.add(u.user_hash)

                user_idx += 1

        self.user_weights = np.array([u.activity_weight for u in self.users], dtype=np.float64)
        self.user_weights /= self.user_weights.sum()

    def _evaluate_external_disturbance(self, evt_time: datetime) -> float:
        """
        Calculates time-varying external disturbance factor D_t affecting both treatment and control cohorts.
        SUTVA assumption: Common time-varying shock affects both cohorts comparably.
        """
        dist = self.config.external_disturbance
        if dist.disturbance_type == ExternalDisturbanceType.NONE or not dist.onset_time:
            return 1.0

        onset = dist.onset_time
        end_time = onset + timedelta(minutes=dist.duration_minutes)

        if onset <= evt_time <= end_time:
            return dist.magnitude
        return 1.0

    def generate_events(self) -> List[EngagementEvent]:
        """
        Generates deterministic stream of validated EngagementEvent objects for Treatment & Control cohorts.
        Strict Firewall: Emitted events contain ZERO hidden policy parameter state or ground-truth effect sizes.
        """
        events: List[EngagementEvent] = []
        is_fixed_count = self.config.num_events is not None
        target_event_count = self.config.num_events if is_fixed_count else (self.config.event_rate * 60)
        
        start_time = self.config.start_time
        duration_sec = self.config.duration_hours * 3600.0
        t0 = self.config.t0 or (start_time + timedelta(hours=self.config.duration_hours / 2.0))

        # Generator loop until target event count is met
        num_impressions = target_event_count * 2
        selected_user_indices = self.np_rng.choice(
            len(self.users), size=num_impressions, p=self.user_weights
        )

        legacy_pid = getattr(self, "legacy_policy_id", "P001")

        for i in range(num_impressions):
            if is_fixed_count and len(events) >= target_event_count:
                break

            user = self.users[selected_user_indices[i]]
            is_treatment = user.user_hash in self.treatment_user_hashes

            # Distribute timestamps uniformly across duration_hours for generated events
            current_count = len(events)
            progress_ratio = (current_count / float(target_event_count)) if is_fixed_count else (i / float(num_impressions))
            offset_sec = progress_ratio * duration_sec
            evt_time = start_time + timedelta(seconds=offset_sec)
            is_post_t0 = evt_time >= t0

            # 1. Fetch candidate items from catalog
            candidates = self.catalog.get_candidate_items(count=15)

            # 2. Recommendation Engine scores and ranks candidate items
            # Treatment cohort ranking weights shift post-T0; Control cohort is preserved (SUTVA no-interference)
            recommended_items = self.recommender.rank_candidates(
                user=user,
                candidates=candidates,
                is_treatment=is_treatment,
                is_post_t0=is_post_t0,
                mechanism=self.config.policy_mechanism,
                params=self.config.policy_params,
                top_k=1,
            )
            top_item = recommended_items[0]

            # 3. User Behavioral Emergence (Watch Completion -> Engagement)
            outcome = self.behavior_model.process_impression(user=user, item=top_item, rng=self.py_rng)

            # 4. Apply external time-varying disturbance D_t (affects treatment & control comparably)
            dist_multiplier = self._evaluate_external_disturbance(evt_time)
            if dist_multiplier < 1.0 and self.py_rng.random() > dist_multiplier:
                continue  # Suppressed by external disturbance shock

            # 5. Emit anonymized events for generated user actions
            cohort_tag = "treatment" if is_treatment else "control"
            policy_state_str = legacy_pid if (is_post_t0 and self.timeline) else "pre_policy"

            # Always emit View
            events.append(
                EventValidator.validate_and_parse({
                    "event_id": f"evt_{len(events)+1:08d}",
                    "user_hash": user.user_hash,
                    "metric_type": MetricType.VIEW.value,
                    "value": 1.0,
                    "timestamp": evt_time.isoformat(),
                    "content_category": top_item.category,
                    "segment_metadata": {"user_segment": user.segment.value, "cohort": cohort_tag},
                    "policy_state": policy_state_str,
                })
            )
            if is_fixed_count and len(events) >= target_event_count:
                break

            if outcome.liked:
                events.append(
                    EventValidator.validate_and_parse({
                        "event_id": f"evt_{len(events)+1:08d}",
                        "user_hash": user.user_hash,
                        "metric_type": MetricType.LIKE.value,
                        "value": 1.0,
                        "timestamp": evt_time.isoformat(),
                        "content_category": top_item.category,
                        "segment_metadata": {"user_segment": user.segment.value, "cohort": cohort_tag},
                        "policy_state": policy_state_str,
                    })
                )
                if is_fixed_count and len(events) >= target_event_count:
                    break

            if outcome.commented:
                # Apply legacy comment suppression adapter if active
                if is_post_t0 and self.legacy_comment_suppression < 1.0:
                    if self.py_rng.random() > self.legacy_comment_suppression:
                        pass
                    else:
                        events.append(
                            EventValidator.validate_and_parse({
                                "event_id": f"evt_{len(events)+1:08d}",
                                "user_hash": user.user_hash,
                                "metric_type": MetricType.COMMENT.value,
                                "value": 1.0,
                                "timestamp": evt_time.isoformat(),
                                "content_category": top_item.category,
                                "segment_metadata": {"user_segment": user.segment.value, "cohort": cohort_tag},
                                "policy_state": policy_state_str,
                            })
                        )
                else:
                    events.append(
                        EventValidator.validate_and_parse({
                            "event_id": f"evt_{len(events)+1:08d}",
                            "user_hash": user.user_hash,
                            "metric_type": MetricType.COMMENT.value,
                            "value": 1.0,
                            "timestamp": evt_time.isoformat(),
                            "content_category": top_item.category,
                            "segment_metadata": {"user_segment": user.segment.value, "cohort": cohort_tag},
                            "policy_state": policy_state_str,
                        })
                    )
                if is_fixed_count and len(events) >= target_event_count:
                    break

            if outcome.shared:
                events.append(
                    EventValidator.validate_and_parse({
                        "event_id": f"evt_{len(events)+1:08d}",
                        "user_hash": user.user_hash,
                        "metric_type": MetricType.SHARE.value,
                        "value": 1.0,
                        "timestamp": evt_time.isoformat(),
                        "content_category": top_item.category,
                        "segment_metadata": {"user_segment": user.segment.value, "cohort": cohort_tag},
                        "policy_state": policy_state_str,
                    })
                )
                if is_fixed_count and len(events) >= target_event_count:
                    break

            if outcome.clicked:
                events.append(
                    EventValidator.validate_and_parse({
                        "event_id": f"evt_{len(events)+1:08d}",
                        "user_hash": user.user_hash,
                        "metric_type": MetricType.CLICK.value,
                        "value": 1.0,
                        "timestamp": evt_time.isoformat(),
                        "content_category": top_item.category,
                        "segment_metadata": {"user_segment": user.segment.value, "cohort": cohort_tag},
                        "policy_state": policy_state_str,
                    })
                )
                if is_fixed_count and len(events) >= target_event_count:
                    break

            # Emit Session Duration
            events.append(
                EventValidator.validate_and_parse({
                    "event_id": f"evt_{len(events)+1:08d}",
                    "user_hash": user.user_hash,
                    "metric_type": MetricType.SESSION_DURATION.value,
                    "value": outcome.watch_time_seconds,
                    "timestamp": evt_time.isoformat(),
                    "content_category": top_item.category,
                    "segment_metadata": {"user_segment": user.segment.value, "cohort": cohort_tag},
                    "policy_state": policy_state_str,
                })
            )
            if is_fixed_count and len(events) >= target_event_count:
                break

        events.sort(key=lambda e: e.timestamp)
        return events[:target_event_count] if is_fixed_count else events
