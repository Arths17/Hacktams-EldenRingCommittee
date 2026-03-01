"""
API exception classes and error handling utilities for HealthOS.
"""

from fastapi.responses import JSONResponse
from fastapi import status
from typing import Optional


class HealthOSAPIError(Exception):
    """Base exception for HealthOS API errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[dict] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_response(self) -> JSONResponse:
        """Convert exception to FastAPI JSONResponse."""
        return JSONResponse(
            status_code=self.status_code,
            content={
                "success": False,
                "error": self.message,
                "error_code": self.error_code,
                **({"details": self.details} if self.details else {}),
            },
        )


class AuthenticationError(HealthOSAPIError):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_FAILED",
            details=details,
        )


class AuthorizationError(HealthOSAPIError):
    """Raised when user lacks required permissions."""
    
    def __init__(self, message: str = "Insufficient permissions", details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
            details=details,
        )


class ValidationError(HealthOSAPIError):
    """Raised when request validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[dict] = None):
        full_details = details or {}
        if field:
            full_details["field"] = field
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=full_details,
        )


class ResourceNotFoundError(HealthOSAPIError):
    """Raised when a requested resource is not found."""
    
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details={"resource": resource, "identifier": identifier},
        )


class RateLimitError(HealthOSAPIError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after},
        )


class ConflictError(HealthOSAPIError):
    """Raised when request conflicts with existing resource."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
            details=details,
        )


class InternalServerError(HealthOSAPIError):
    """Raised for internal server errors."""
    
    def __init__(self, message: str = "Internal server error", details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR",
            details=details,
        )


class ExternalServiceError(HealthOSAPIError):
    """Raised when external service (Supabase, Ollama, etc.) fails."""
    
    def __init__(self, service: str, message: str, details: Optional[dict] = None):
        full_details = details or {}
        full_details["service"] = service
        super().__init__(
            message=f"{service} service error: {message}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE",
            details=full_details,
        )
