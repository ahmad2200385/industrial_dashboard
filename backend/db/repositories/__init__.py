"""Repository implementations for database models."""

from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from common.base import BaseRepository
from common.exceptions import ResourceNotFoundException
from models.alert import Alert
from models.machine import Machine
from models.sensor_data import SensorData


class MachineRepository(BaseRepository[Machine]):
    """Repository for Machine model operations."""

    def __init__(self):
        super().__init__(Machine)

    def get_by_name(self, db: Session, name: str) -> Optional[Machine]:
        """Get machine by name."""
        try:
            return db.query(Machine).filter(Machine.name == name).first()
        except Exception as e:
            from common.exceptions import DatabaseException
            raise DatabaseException(str(e), "get_by_name")

    def get_by_location(self, db: Session, location: str) -> List[Machine]:
        """Get all machines at a location."""
        try:
            return db.query(Machine).filter(Machine.location == location).all()
        except Exception as e:
            from common.exceptions import DatabaseException
            raise DatabaseException(str(e), "get_by_location")


class SensorDataRepository(BaseRepository[SensorData]):
    """Repository for SensorData model operations."""

    def __init__(self):
        super().__init__(SensorData)

    def get_latest_by_machine(
        self, db: Session, machine_id: int, limit: int = 1
    ) -> List[SensorData]:
        """Get latest sensor readings for a machine."""
        try:
            return (
                db.query(SensorData)
                .filter(SensorData.machine_id == machine_id)
                .order_by(SensorData.timestamp.desc())
                .limit(limit)
                .all()
            )
        except Exception as e:
            from common.exceptions import DatabaseException
            raise DatabaseException(str(e), "get_latest_by_machine")

    def get_by_machine_and_status(
        self, db: Session, machine_id: int, status: str
    ) -> List[SensorData]:
        """Get sensor readings by machine and status."""
        try:
            return db.query(SensorData).filter(
                and_(
                    SensorData.machine_id == machine_id,
                    SensorData.status == status,
                )
            ).all()
        except Exception as e:
            from common.exceptions import DatabaseException
            raise DatabaseException(str(e), "get_by_machine_and_status")


class AlertRepository(BaseRepository[Alert]):
    """Repository for Alert model operations."""

    def __init__(self):
        super().__init__(Alert)

    def get_active_by_machine(
        self, db: Session, machine_id: int
    ) -> List[Alert]:
        """Get active alerts for a machine."""
        try:
            return db.query(Alert).filter(
                and_(
                    Alert.machine_id == machine_id,
                    Alert.state == "ACTIVE",
                )
            ).all()
        except Exception as e:
            from common.exceptions import DatabaseException
            raise DatabaseException(str(e), "get_active_by_machine")

    def get_by_level(
        self, db: Session, level: str, limit: int = 100
    ) -> List[Alert]:
        """Get alerts by severity level."""
        try:
            return (
                db.query(Alert)
                .filter(Alert.level == level)
                .order_by(Alert.created_at.desc())
                .limit(limit)
                .all()
            )
        except Exception as e:
            from common.exceptions import DatabaseException
            raise DatabaseException(str(e), "get_by_level")

    def get_unresolved_critical(self, db: Session) -> List[Alert]:
        """Get all unresolved critical alerts."""
        try:
            return db.query(Alert).filter(
                and_(
                    Alert.state == "ACTIVE",
                    Alert.level == "CRITICAL",
                )
            ).order_by(Alert.created_at.desc()).all()
        except Exception as e:
            from common.exceptions import DatabaseException
            raise DatabaseException(str(e), "get_unresolved_critical")