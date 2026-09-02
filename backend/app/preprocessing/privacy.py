"""
Privacy Enforcement and Data Minimization Layer for CAGED.
"""

import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple
from app.config import settings
from app.core.exceptions import CAGEDException


class PrivacyViolationException(CAGEDException):
    """Raised when an incoming event payload contains forbidden private content or unhashed PII."""

    def __init__(self, message: str = "Privacy violation: forbidden content or raw PII detected"):
        super().__init__(message=message, status_code=400)


# Explicit list of forbidden private-content and sensitive PII attributes
FORBIDDEN_FIELDS: Set[str] = {
    "message_content",
    "private_message",
    "chat_history",
    "password",
    "secret",
    "private_photo",
    "private_video",
    "private_document",
    "contact_list",
    "email",
    "phone",
    "phone_number",
    "real_name",
    "full_name",
    "ssn",
    "social_security_number",
    "exact_location",
    "gps_coordinates",
    "street_address",
    "credit_card",
    "biometric_data",
}


def pseudonymize_user_id(raw_user_id: str, salt: Optional[str] = None) -> str:
    """
    Computes a deterministic, non-reversible SHA-256 pseudonymous hash for a user ID.
    
    Args:
        raw_user_id: Raw string identifier (e.g. account ID).
        salt: Secret salt for HMAC-like hashing. Defaults to settings.HASH_SALT.
        
    Returns:
        64-character hexadecimal SHA-256 string.
    """
    effective_salt = salt or settings.HASH_SALT
    combined = f"{raw_user_id}:{effective_salt}".encode("utf-8")
    return hashlib.sha256(combined).hexdigest()


class PrivacySanitizer:
    """Sanitizer service enforcing privacy-by-design filtering."""

    @classmethod
    def scan_for_forbidden_keys(cls, data: Any, current_path: str = "") -> List[str]:
        """
        Recursively scans dictionary or list structures for any keys matching FORBIDDEN_FIELDS.
        
        Returns:
            List of JSON-path style strings representing detected forbidden keys.
        """
        detected: List[str] = []

        if isinstance(data, dict):
            for key, val in data.items():
                key_lower = str(key).lower()
                path = f"{current_path}.{key}" if current_path else str(key)
                
                if key_lower in FORBIDDEN_FIELDS:
                    detected.append(path)
                
                detected.extend(cls.scan_for_forbidden_keys(val, path))
        elif isinstance(data, list):
            for idx, item in enumerate(data):
                path = f"{current_path}[{idx}]"
                detected.extend(cls.scan_for_forbidden_keys(item, path))

        return detected

    @classmethod
    def sanitize_event_dict(cls, payload: Dict[str, Any], strict_reject: bool = True) -> Dict[str, Any]:
        """
        Sanitizes or validates an event payload dict against privacy boundaries.
        
        Args:
            payload: Raw input dictionary representing an engagement event.
            strict_reject: If True, raises PrivacyViolationException upon finding any forbidden field.
            
        Returns:
            Sanitized dictionary.
            
        Raises:
            PrivacyViolationException if strict_reject is True and forbidden keys are found.
        """
        forbidden_matches = cls.scan_for_forbidden_keys(payload)
        
        if forbidden_matches:
            if strict_reject:
                raise PrivacyViolationException(
                    f"Event payload contains forbidden private fields: {', '.join(forbidden_matches)}"
                )
            
            # If not strict, purge detected fields
            sanitized = payload.copy()
            for forbidden_path in forbidden_matches:
                parts = forbidden_path.split(".")
                curr = sanitized
                for part in parts[:-1]:
                    if isinstance(curr, dict) and part in curr:
                        curr = curr[part]
                if isinstance(curr, dict) and parts[-1] in curr:
                    del curr[parts[-1]]
            return sanitized

        return payload
