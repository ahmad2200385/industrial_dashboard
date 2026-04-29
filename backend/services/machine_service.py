"""Machine service implementing business logic for machine operations."""
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from common import BaseService, ResourceNotFoundException, ValidationException
from db.repositories import MachineRepository
from models.machine import Machine
from utils import Validator, log_operation


class MachineService(BaseService):
    """Service for machine-related operations.
    
    Handles business logic for machine CRUD operations,
    validation, and related business rules.
    """
    
    def __init__(self):
        """Initialize machine service with repository."""
        self.repository = MachineRepository()
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate machine input data.
        
        Args:
            data: Machine data to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationException: If validation fails
        """
        super().validate_input(data)
        
        if 'name' in data:
            Validator.validate_string(data['name'], 'name', min_length=1, max_length=256)
        
        if 'location' in data:
            Validator.validate_string(data['location'], 'location', min_length=1, max_length=256)
        
        return True
    
    @log_operation("create_machine")
    def create_machine(self, db: Session, name: str, location: str) -> Machine:
        """Create a new machine.
        
        Args:
            db: Database session
            name: Machine name
            location: Machine location
            
        Returns:
            Created Machine object
            
        Raises:
            ValidationException: If input is invalid
            DatabaseException: If database operation fails
        """
        self.validate_input({'name': name, 'location': location})
        
        # Check if machine with same name exists
        existing = self.repository.get_by_name(db, name)
        if existing:
            raise ValidationException(
                f"Machine with name '{name}' already exists",
                {"name": name}
            )
        
        return self.repository.create(db, {
            'name': name,
            'location': location
        })
    
    @log_operation("list_machines")
    def list_machines(self, db: Session, skip: int = 0, limit: int = 100) -> List[Machine]:
        """List all machines.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Number of records to return
            
        Returns:
            List of Machine objects
        """
        Validator.validate_non_negative_int(skip, 'skip')
        Validator.validate_positive_int(limit, 'limit')
        return self.repository.get_all(db, skip=skip, limit=limit)
    
    @log_operation("get_machine")
    def get_machine(self, db: Session, machine_id: int) -> Machine:
        """Get machine by ID.
        
        Args:
            db: Database session
            machine_id: Machine ID
            
        Returns:
            Machine object
            
        Raises:
            ResourceNotFoundException: If machine not found
        """
        machine = self.repository.get_by_id(db, machine_id)
        if not machine:
            raise ResourceNotFoundException('Machine', machine_id)
        return machine
    
    @log_operation("update_machine")
    def update_machine(self, db: Session, machine_id: int, update_data: Dict[str, Any]) -> Machine:
        """Update machine.
        
        Args:
            db: Database session
            machine_id: Machine ID to update
            update_data: Fields to update
            
        Returns:
            Updated Machine object
            
        Raises:
            ValidationException: If validation fails
            ResourceNotFoundException: If machine not found
        """
        self.validate_input(update_data)
        return self.repository.update(db, machine_id, update_data)
    
    @log_operation("delete_machine")
    def delete_machine(self, db: Session, machine_id: int) -> bool:
        """Delete machine.
        
        Args:
            db: Database session
            machine_id: Machine ID to delete
            
        Returns:
            True if deleted
            
        Raises:
            ResourceNotFoundException: If machine not found
        """
        return self.repository.delete(db, machine_id)
    
    def get_machines_by_location(self, db: Session, location: str) -> List[Machine]:
        """Get all machines at a location.
        
        Args:
            db: Database session
            location: Location name
            
        Returns:
            List of Machine objects
        """
        Validator.validate_string(location, 'location')
        return self.repository.get_by_location(db, location)

    def get_or_404(self, db: Session, machine_id: int) -> Machine:
        """Get a machine or raise ResourceNotFoundException."""
        return self.get_machine(db, machine_id)

    @staticmethod
    def to_payload(machine: Machine) -> Dict[str, Any]:
        """Serialize machine model for API/WebSocket payloads."""
        return {
            "id": machine.id,
            "name": machine.name,
            "location": machine.location,
            "created_at": machine.created_at.isoformat() if machine.created_at else None,
        }
