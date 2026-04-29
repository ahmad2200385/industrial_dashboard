from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

from schemas.base import ORMBase


class SensorDataBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    machine_id: int = Field(..., gt=0)
    temperature: float = Field(..., ge=-100.0, le=400.0)
    status: str = Field(..., min_length=1, max_length=32)
    production_count: int = Field(..., ge=0)
    timestamp: datetime

    @field_validator('status')
    @classmethod
    def normalize_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError('status must not be empty')
        return normalized

    @field_validator('timestamp')
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class SensorDataCreate(SensorDataBase):
    pass


class SensorData(SensorDataBase, ORMBase):
    id: int
    created_at: datetime
