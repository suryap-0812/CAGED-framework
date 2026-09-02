"""
Event Validation Pipeline for CAGED Framework.
"""

from typing import Any, Dict
from pydantic import ValidationError
from app.core.exceptions import ValidationException
from app.ingestion.models import EngagementEvent
from app.preprocessing.privacy import PrivacySanitizer


class EventValidator:
    """Validates raw incoming events through privacy filtering and schema validation."""

    @classmethod
    def validate_and_parse(cls, payload: Dict[str, Any]) -> EngagementEvent:
        """
        Processes a raw event dictionary through privacy screening and model instantiation.
        
        Args:
            payload: Raw event dictionary.
            
        Returns:
            Validated EngagementEvent instance.
            
        Raises:
            PrivacyViolationException: If forbidden private content is found.
            ValidationException: If schema, timestamp, or metric validation fails.
        """
        # Step 1: Privacy & Data-Minimization Screening
        sanitized_dict = PrivacySanitizer.sanitize_event_dict(payload, strict_reject=True)

        # Step 2: Canonical Pydantic Schema Parsing
        try:
            event = EngagementEvent(**sanitized_dict)
            return event
        except ValidationError as err:
            errors_str = "; ".join([f"{e['loc']}: {e['msg']}" for e in err.errors()])
            raise ValidationException(f"Event payload validation failed: {errors_str}")
