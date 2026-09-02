"""
Policy Trigger Service for Dynamic Stream Policy Injection.
"""

from datetime import datetime, timezone
from typing import Callable, List, Optional
from app.core.logging import get_logger
from app.policy.models import PolicyEvent
from app.policy.registry import PolicyTimeline

logger = get_logger(__name__)

PolicyCallback = Callable[[PolicyEvent], None]


class PolicyTrigger:
    """
    Service responsible for triggering policy changes and notifying subscribers.
    """

    def __init__(self, timeline: Optional[PolicyTimeline] = None):
        self.timeline = timeline or PolicyTimeline()
        self.listeners: List[PolicyCallback] = []

    def register_listener(self, callback: PolicyCallback) -> None:
        """Registers a callback subscriber for policy trigger events."""
        self.listeners.append(callback)

    def trigger_policy(self, policy: PolicyEvent) -> None:
        """
        Triggers a policy event, registers it on the timeline, and notifies listeners.
        """
        logger.info("Triggering Policy Event '%s' (%s) at %s", policy.policy_id, policy.policy_name, policy.timestamp.isoformat())
        self.timeline.add_policy_event(policy)
        
        for listener in self.listeners:
            try:
                listener(policy)
            except Exception as err:
                logger.error("Error notifying policy listener: %s", err, exc_info=True)
