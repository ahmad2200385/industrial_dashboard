from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from schemas.base import ORMBase


class MachineBase(BaseModel):
    name: str
    location: str


class MachineCreate(MachineBase):
    pass


class MachineUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None


class Machine(MachineBase, ORMBase):
    id: int
    created_at: datetime
