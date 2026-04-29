from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from schemas.base import ORMBase

AlertLevel = Literal['INFO', 'WARNING', 'CRITICAL']
AlertState = Literal['ACTIVE', 'RESOLVED', 'EXPIRED']


class AlertBase(BaseModel):
    machine_id: int
    alert_type: str
    message: str
    level: AlertLevel = 'INFO'


class AlertCreate(AlertBase):
    pass


class Alert(AlertBase, ORMBase):
    id: int
    state: AlertState
    expires_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AlertResolve(BaseModel):
    reason: str | None = None
