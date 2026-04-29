"""Alert service implementing business logic for alert operations."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from common import BaseService, ResourceNotFoundException, ValidationException
from core.config import settings
from db.repositories import AlertRepository
from models.alert import Alert
from utils import Validator, log_operation


class AlertService(BaseService):
    """Service for alert-related operations."""

    LEVEL_INFO = "INFO"
    LEVEL_WARNING = "WARNING"
    LEVEL_CRITICAL = "CRITICAL"

    VALID_LEVELS = {LEVEL_INFO, LEVEL_WARNING, LEVEL_CRITICAL}

    STATE_ACTIVE = "ACTIVE"
    STATE_RESOLVED = "RESOLVED"
    STATE_EXPIRED = "EXPIRED"

    VALID_STATES = {STATE_ACTIVE, STATE_RESOLVED, STATE_EXPIRED}

    TTL_BY_LEVEL = {
        LEVEL_INFO: settings.ALERT_INFO_TTL_SECONDS,
        LEVEL_WARNING: settings.ALERT_WARNING_TTL_SECONDS,
        LEVEL_CRITICAL: settings.ALERT_CRITICAL_TTL_SECONDS,
    }

    def __init__(self):
        self.repository = AlertRepository()

    def validate_input(self, data: Dict[str, Any]) -> bool:
        super().validate_input(data)

        if "alert_type" in data:
            Validator.validate_string(
                data["alert_type"], "alert_type", min_length=1, max_length=64
            )

        if "message" in data:
            Validator.validate_string(
                data["message"], "message", min_length=1, max_length=512
            )

        if "level" in data:
            Validator.validate_enum(data["level"], list(self.VALID_LEVELS), "level")

        if "machine_id" in data:
            Validator.validate_positive_int(data["machine_id"], "machine_id")

        return True

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @classmethod
    def _normalize_level(cls, level: str) -> str:
        normalized = (level or "").upper().strip()
        return normalized if normalized in cls.VALID_LEVELS else cls.LEVEL_INFO

    @classmethod
    def _get_expiry_for_level(cls, level: str) -> datetime:
        ttl = cls.TTL_BY_LEVEL.get(level, settings.ALERT_WARNING_TTL_SECONDS)
        return datetime.now(timezone.utc) + timedelta(seconds=max(ttl, 1))

    @log_operation("create_alert")
    def create_alert(
        self,
        db: Session,
        machine_id: int,
        alert_type: str,
        message: str,
        level: str = "INFO",
    ) -> Alert:

        self.validate_input(
            {
                "machine_id": machine_id,
                "alert_type": alert_type,
                "message": message,
                "level": level,
            }
        )

        from models.machine import Machine

        machine = db.query(Machine).filter(Machine.id == machine_id).first()
        if not machine:
            raise ResourceNotFoundException("Machine", machine_id)

        normalized_level = self._normalize_level(level)

        return self.repository.create(
            db,
            {
                "machine_id": machine_id,
                "alert_type": alert_type,
                "message": message,
                "level": normalized_level,
                "state": self.STATE_ACTIVE,
                "expires_at": self._get_expiry_for_level(normalized_level),
            },
        )

    @log_operation("expire_due_alerts")
    def expire_due_alerts(self, db: Session) -> List[Alert]:
        """Expire alerts that are past their expiry time."""

        now = self._now()

        due_alerts = (
            db.query(Alert)
            .filter(
                Alert.state == self.STATE_ACTIVE,
                Alert.expires_at.isnot(None),
                Alert.expires_at <= now,
            )
            .all()
        )

        if not due_alerts:
            return []

        for alert in due_alerts:
            alert.state = self.STATE_EXPIRED
            alert.resolved_at = now

        db.commit()

        for alert in due_alerts:
            db.refresh(alert)

        return due_alerts

    def list(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
    ) -> List[Alert]:
        """List alerts with optional active-only filtering."""
        Validator.validate_non_negative_int(skip, "skip")
        Validator.validate_positive_int(limit, "limit")

        if active_only:
            return (
                db.query(Alert)
                .filter(Alert.state == self.STATE_ACTIVE)
                .order_by(Alert.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )

        return self.repository.get_all(db, skip=skip, limit=limit)

    @log_operation("resolve_alert")
    def resolve_alert(self, db: Session, alert_id: int) -> Alert:
        """Resolve an existing alert."""
        alert = self.repository.get_by_id(db, alert_id)
        if not alert:
            raise ResourceNotFoundException("Alert", alert_id)

        alert.state = self.STATE_RESOLVED
        alert.resolved_at = self._now()
        db.commit()
        db.refresh(alert)
        return alert

    def get_active_by_machine(self, db: Session, machine_id: int) -> List[Alert]:
        Validator.validate_positive_int(machine_id, "machine_id")
        return self.repository.get_active_by_machine(db, machine_id)

    def get_critical_unresolved(self, db: Session) -> List[Alert]:
        return self.repository.get_unresolved_critical(db)

    @staticmethod
    def to_payload(alert: Alert) -> Dict[str, Any]:
        """Serialize alert model for API/WebSocket payloads."""
        return {
            "id": alert.id,
            "machine_id": alert.machine_id,
            "alert_type": alert.alert_type,
            "message": alert.message,
            "level": alert.level,
            "state": alert.state,
            "expires_at": alert.expires_at.isoformat() if alert.expires_at else None,
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
            "updated_at": alert.updated_at.isoformat() if alert.updated_at else None,
        }
