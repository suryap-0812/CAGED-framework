"""
Policy Registry and Chronological Policy Timeline Manager.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.core.exceptions import ResourceNotFoundException
from app.policy.models import PolicyEvent


class PolicyRegistry:
    """Central repository storing all registered policy events."""

    def __init__(self):
        self._policies: Dict[str, PolicyEvent] = {}

    def register_policy(self, policy: PolicyEvent) -> None:
        """Registers a new PolicyEvent."""
        self._policies[policy.policy_id] = policy

    def get_policy(self, policy_id: str) -> PolicyEvent:
        """Retrieves a registered PolicyEvent by policy_id."""
        if policy_id not in self._policies:
            raise ResourceNotFoundException(f"Policy '{policy_id}' not found in registry.")
        return self._policies[policy_id]

    def list_policies(self) -> List[PolicyEvent]:
        """Returns all registered policies sorted by timestamp."""
        return sorted(list(self._policies.values()), key=lambda p: p.timestamp)

    def clear(self) -> None:
        """Clears registry."""
        self._policies.clear()


class PolicyTimeline:
    """Manages chronological timeline of policy triggers and status checks."""

    def __init__(self, registry: Optional[PolicyRegistry] = None):
        self.registry = registry or PolicyRegistry()

    def add_policy_event(self, policy: PolicyEvent) -> None:
        """Adds a policy event to the timeline via registry."""
        self.registry.register_policy(policy)

    def get_all_policy_events(self) -> List[PolicyEvent]:
        """Returns all registered policy events sorted by timestamp."""
        return self.registry.list_policies()

    def get_active_policies_at(self, timestamp: datetime) -> List[PolicyEvent]:
        """
        Returns all policies that took effect on or before timestamp.
        """
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = timestamp.astimezone(timezone.utc)

        all_policies = self.registry.list_policies()
        return [p for p in all_policies if p.timestamp <= timestamp]

    def is_policy_active(self, policy_id: str, timestamp: datetime) -> bool:
        """
        Checks whether a specific policy is active at a given timestamp.
        """
        policy = self.registry.get_policy(policy_id)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = timestamp.astimezone(timezone.utc)
            
        return policy.timestamp <= timestamp

    def get_latest_policy_before(self, timestamp: datetime) -> Optional[PolicyEvent]:
        """Returns the most recent policy that took effect before timestamp."""
        active = self.get_active_policies_at(timestamp)
        return active[-1] if active else None
