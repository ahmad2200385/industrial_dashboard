"""
Custom exception classes for the application.
Follows OOP principles for centralized error handling.
"""
from typing import Any, Dict, Optional


class ApplicationException(Exception):
    """Base exception for all application-specific errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the application exception.
        
        Args:
            message: Human-readable error message
            error_code: Unique error code for categorization
            status_code: HTTP status code
            details: Additional error context
        """
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


class ResourceNotFoundException(ApplicationException):
    """Raised when a requested resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: Any):
        super().__init__(
            message=f"{resource_type} with id {resource_id} not found",
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            details={"resource_type": resource_type, "resource_id": str(resource_id)}
        )


class ResourceAlreadyExistsException(ApplicationException):
    """Raised when attempting to create a duplicate resource."""
    
    def __init__(self, resource_type: str, details: Optional[Dict] = None):
        super().__init__(
            message=f"{resource_type} already exists",
            error_code="RESOURCE_ALREADY_EXISTS",
            status_code=409,
            details=details or {}
        )


class ValidationException(ApplicationException):
    """Raised when request validation fails."""
    
    def __init__(self, message: str, fields: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details={"fields": fields or {}}
        )


class DatabaseException(ApplicationException):
    """Raised when database operations fail."""
    
    def __init__(self, message: str, operation: str = "unknown"):
        super().__init__(
            message=f"Database error during {operation}: {message}",
            error_code="DATABASE_ERROR",
            status_code=500,
            details={"operation": operation}
        )


class ServiceException(ApplicationException):
    """Raised when service operations fail."""
    
    def __init__(self, service_name: str, message: str):
        super().__init__(
            message=f"{service_name} service error: {message}",
            error_code="SERVICE_ERROR",
            status_code=500,
            details={"service": service_name}
        )


class ConfigurationException(ApplicationException):
    """Raised when configuration is invalid."""
    
    def __init__(self, config_key: str, message: str):
        super().__init__(
            message=f"Configuration error for {config_key}: {message}",
            error_code="CONFIG_ERROR",
            status_code=500,
            details={"config_key": config_key}
        )


class OperationTimeoutException(ApplicationException):
    """Raised when an operation times out."""
    
    def __init__(self, operation: str, timeout_seconds: float):
        super().__init__(
            message=f"Operation '{operation}' timed out after {timeout_seconds}s",
            error_code="OPERATION_TIMEOUT",
            status_code=504,
            details={"operation": operation, "timeout_seconds": timeout_seconds}
        )
