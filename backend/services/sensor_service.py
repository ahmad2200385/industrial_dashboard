"""Sensor service implementing business logic for sensor data operations."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from common import BaseService, ResourceNotFoundException, ValidationException
from core.config import settings
from db.repositories import AlertRepository, SensorDataRepository
from models.alert import Alert
from models.machine import Machine
from models.sensor_data import SensorData
from services.alert_service import AlertService
from services.redis_service import redis_manager
from utils import Validator, log_operation, measure_performance


class SensorService(BaseService):
    """Service for sensor data operations.

    Handles sensor data creation, validation, and related alerts.
    """

    VALID_STATUSES = {"normal", "warning", "error"}

    def __init__(self):
        self.repository = SensorDataRepository()
        self.alert_repository = AlertRepository()
        self.alert_service = AlertService()

    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate sensor data input."""
        super().validate_input(data)

        if "machine_id" in data:
            Validator.validate_positive_int(data["machine_id"], "machine_id")

        if "temperature" in data:
            Validator.validate_range(data["temperature"], -50, 150, "temperature")

        if "status" in data:
            Validator.validate_enum(data["status"], list(self.VALID_STATUSES), "status")

        if "production_count" in data:
            value = int(data["production_count"])
            if value < 0:
                raise ValidationException(
                    "production_count must be non-negative",
                    {"field": "production_count", "value": value},
                )

        return True

    @log_operation("create_sensor_data")
    @measure_performance(threshold_ms=500)
    def create_sensor_data(
        self,
        db: Session,
        machine_id: int,
        temperature: float,
        status: str,
        production_count: int,
        timestamp: datetime,
    ) -> Tuple[SensorData, List[Alert]]:
        """Create sensor data and related alerts."""

        self.validate_input(
            {
                "machine_id": machine_id,
                "temperature": temperature,
                "status": status.lower(),
                "production_count": production_count,
            }
        )

        machine = db.query(Machine).filter(Machine.id == machine_id).first()
        if not machine:
            raise ResourceNotFoundException("Machine", machine_id)

        normalized_ts = (
            timestamp.astimezone(timezone.utc)
            if timestamp
            else datetime.now(timezone.utc)
        )
        normalized_status = status.lower()

        db_sensor_data = SensorData(
            machine_id=machine_id,
            temperature=temperature,
            status=normalized_status,
            production_count=production_count,
            timestamp=normalized_ts,
        )

        alerts = self._generate_alerts(machine_id, temperature, normalized_status)

        db.add(db_sensor_data)
        if alerts:
            db.add_all(alerts)

        db.commit()
        db.refresh(db_sensor_data)
        for alert in alerts:
            db.refresh(alert)

        self._cache_sensor_state(
            machine_id,
            temperature,
            normalized_status,
            production_count,
            normalized_ts,
        )

        return db_sensor_data, alerts

    def _generate_alerts(
        self, machine_id: int, temperature: float, status: str
    ) -> List[Alert]:
        """Generate alerts based on sensor readings."""
        alerts: List[Alert] = []
        alert_service = AlertService()

        if temperature > settings.ALERT_TEMPERATURE_THRESHOLD:
            alerts.append(
                Alert(
                    machine_id=machine_id,
                    alert_type="temperature",
                    level=AlertService.LEVEL_WARNING,
                    state=AlertService.STATE_ACTIVE,
                    message=(
                        f"Temperature alert: {temperature}°C exceeds "
                        f"threshold of {settings.ALERT_TEMPERATURE_THRESHOLD}°C"
                    ),
                    expires_at=alert_service._get_expiry_for_level(
                        AlertService.LEVEL_WARNING
                    ),
                )
            )

        if status == "error":
            alerts.append(
                Alert(
                    machine_id=machine_id,
                    alert_type="status",
                    level=AlertService.LEVEL_CRITICAL,
                    state=AlertService.STATE_ACTIVE,
                    message="Machine in error state",
                    expires_at=alert_service._get_expiry_for_level(
                        AlertService.LEVEL_CRITICAL
                    ),
                )
            )

        return alerts

    def _cache_sensor_state(
        self,
        machine_id: int,
        temperature: float,
        status: str,
        production_count: int,
        timestamp: datetime,
    ) -> None:
        """Cache latest sensor state in Redis."""
        state = {
            "machine_id": machine_id,
            "temperature": temperature,
            "status": status,
            "production_count": production_count,
            "timestamp": timestamp.isoformat(),
        }

        try:
            redis_manager.cache_latest_state(machine_id, state)
            redis_manager.cache_sensor_data(machine_id, state)
        except Exception as e:
            from core.logging import get_logger

            logger = get_logger(__name__)
            logger.warning(f"Failed to cache sensor state: {str(e)}")

    @log_operation("list_sensor_data")
    def list_sensor_data(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> List[SensorData]:
        """List sensor data with pagination."""
        Validator.validate_non_negative_int(skip, "skip")
        Validator.validate_positive_int(limit, "limit")
        return self.repository.get_all(db, skip=skip, limit=limit)

    def get_latest_by_machine(
        self, db: Session, machine_id: int, limit: int = 10
    ) -> List[SensorData]:
        """Get latest sensor readings for a machine."""
        Validator.validate_positive_int(machine_id, "machine_id")
        Validator.validate_positive_int(limit, "limit")
        return self.repository.get_latest_by_machine(db, machine_id, limit)

    @staticmethod
    def to_payload(sensor_data: SensorData) -> Dict[str, Any]:
        """Serialize sensor data model for API/WebSocket payloads."""
        return {
            "id": sensor_data.id,
            "machine_id": sensor_data.machine_id,
            "temperature": sensor_data.temperature,
            "status": sensor_data.status,
            "production_count": sensor_data.production_count,
            "timestamp": sensor_data.timestamp.isoformat() if sensor_data.timestamp else None,
            "created_at": sensor_data.created_at.isoformat() if sensor_data.created_at else None,
        }
