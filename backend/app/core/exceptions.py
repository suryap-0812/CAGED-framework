"""
Custom Exception Classes and Error Handlers for CAGED Framework.
"""

from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse


class CAGEDException(Exception):
    """Base exception class for CAGED application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ResourceNotFoundException(CAGEDException):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str = "Requested resource not found"):
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND)


class ValidationException(CAGEDException):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Invalid input parameters"):
        super().__init__(message=message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


async def caged_exception_handler(request: Request, exc: CAGEDException) -> JSONResponse:
    """FastAPI exception handler for CAGED exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
            "path": str(request.url.path),
        },
    )
