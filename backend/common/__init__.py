"""Common utilities and base classes."""
from common.base import BaseRepository, BaseService, CachedService, IRepository, IService
from common.exceptions import (
    ApplicationException,
    ConfigurationException,
    DatabaseException,
    OperationTimeoutException,
    ResourceAlreadyExistsException,
    ResourceNotFoundException,
    ServiceException,
    ValidationException,
)

__all__ = [
    "ApplicationException",
    "ResourceNotFoundException",
    "ResourceAlreadyExistsException",
    "ValidationException",
    "DatabaseException",
    "ServiceException",
    "ConfigurationException",
    "OperationTimeoutException",
    "IRepository",
    "IService",
    "BaseRepository",
    "BaseService",
    "CachedService",
]
