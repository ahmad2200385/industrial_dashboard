"""
Abstract base service class following OOP principles.
All services should inherit from this class for consistency.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

from sqlalchemy.orm import Session

from common.exceptions import ApplicationException

T = TypeVar('T')  # Generic type for model


class IRepository(ABC, Generic[T]):
    """Interface for repository pattern - data access abstraction."""
    
    @abstractmethod
    def get_by_id(self, db: Session, item_id: Any) -> Optional[T]:
        """Get an item by ID."""
        pass
    
    @abstractmethod
    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all items with pagination."""
        pass
    
    @abstractmethod
    def create(self, db: Session, obj: Dict[str, Any]) -> T:
        """Create a new item."""
        pass
    
    @abstractmethod
    def update(self, db: Session, item_id: Any, obj: Dict[str, Any]) -> T:
        """Update an existing item."""
        pass
    
    @abstractmethod
    def delete(self, db: Session, item_id: Any) -> bool:
        """Delete an item."""
        pass


class IService(ABC):
    """Interface for service layer - business logic."""
    
    @abstractmethod
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate input data."""
        pass


class BaseRepository(IRepository[T]):
    """
    Abstract base repository implementing common CRUD operations.
    Provides data access pattern for database operations.
    """
    
    def __init__(self, model_class: type):
        """
        Initialize repository with model class.
        
        Args:
            model_class: SQLAlchemy model class
        """
        self.model_class = model_class
    
    def get_by_id(self, db: Session, item_id: Any) -> Optional[T]:
        """Get item by ID."""
        try:
            return db.query(self.model_class).filter(
                self.model_class.id == item_id
            ).first()
        except Exception as e:
            from common.exceptions import DatabaseException
            raise DatabaseException(str(e), "get_by_id")
    
    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all items with pagination."""
        try:
            return db.query(self.model_class).offset(skip).limit(limit).all()
        except Exception as e:
            from common.exceptions import DatabaseException
            raise DatabaseException(str(e), "get_all")
    
    def create(self, db: Session, obj: Dict[str, Any]) -> T:
        """Create new item."""
        try:
            db_item = self.model_class(**obj)
            db.add(db_item)
            db.commit()
            db.refresh(db_item)
            return db_item
        except Exception as e:
            db.rollback()
            from common.exceptions import DatabaseException
            raise DatabaseException(str(e), "create")
    
    def update(self, db: Session, item_id: Any, obj: Dict[str, Any]) -> T:
        """Update existing item."""
        try:
            db_item = self.get_by_id(db, item_id)
            if not db_item:
                from common.exceptions import ResourceNotFoundException
                raise ResourceNotFoundException(self.model_class.__name__, item_id)
            
            for key, value in obj.items():
                setattr(db_item, key, value)
            
            db.commit()
            db.refresh(db_item)
            return db_item
        except ApplicationException:
            raise
        except Exception as e:
            db.rollback()
            from common.exceptions import DatabaseException
            raise DatabaseException(str(e), "update")
    
    def delete(self, db: Session, item_id: Any) -> bool:
        """Delete item."""
        try:
            db_item = self.get_by_id(db, item_id)
            if not db_item:
                from common.exceptions import ResourceNotFoundException
                raise ResourceNotFoundException(self.model_class.__name__, item_id)
            
            db.delete(db_item)
            db.commit()
            return True
        except ApplicationException:
            raise
        except Exception as e:
            db.rollback()
            from common.exceptions import DatabaseException
            raise DatabaseException(str(e), "delete")


class BaseService(IService):
    """
    Abstract base service implementing common business logic patterns.
    All services should inherit from this class.
    """
    
    def __init__(self, repository: IRepository):
        """
        Initialize service with repository.
        
        Args:
            repository: Repository instance for data access
        """
        self.repository = repository
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """
        Validate input data. Override in child classes.
        
        Args:
            data: Input data to validate
            
        Returns:
            True if valid, raises ValidationException if not
        """
        if not data:
            from common.exceptions import ValidationException
            raise ValidationException("Input data cannot be empty")
        return True
    
    def _check_not_none(self, value: Any, field_name: str) -> None:
        """Helper to validate field is not None."""
        if value is None:
            from common.exceptions import ValidationException
            raise ValidationException(f"{field_name} cannot be None")
    
    def _check_not_empty(self, value: str, field_name: str) -> None:
        """Helper to validate string field is not empty."""
        if not value or not value.strip():
            from common.exceptions import ValidationException
            raise ValidationException(f"{field_name} cannot be empty")


class CachedService(BaseService):
    """
    Extended service with caching support.
    Provides cache management for frequently accessed data.
    """
    
    def __init__(self, repository: IRepository, cache_service: Optional[Any] = None):
        """
        Initialize cached service.
        
        Args:
            repository: Repository instance
            cache_service: Optional cache service instance
        """
        super().__init__(repository)
        self.cache_service = cache_service
    
    def _get_cache_key(self, prefix: str, *args: Any) -> str:
        """Generate cache key from prefix and arguments."""
        return f"{prefix}:{':'.join(str(arg) for arg in args)}"
