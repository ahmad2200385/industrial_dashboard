"""Alert model for system notifications."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.session import Base


class Alert(Base):
    """Represents an alert or notification in the system.
    
    Attributes:
        id: Unique identifier
        machine_id: Reference to affected machine
        alert_type: Category of alert (e.g., 'temperature', 'status')
        level: Severity level (INFO, WARNING, CRITICAL)
        state: Current state (ACTIVE, RESOLVED)
        message: Human-readable alert message
        expires_at: When alert should expire if not resolved
        resolved_at: When alert was resolved
        created_at: When alert was created
        updated_at: When alert was last updated
        machine: Related machine object
    """
    
    __tablename__ = 'alerts'

    id: int = Column(Integer, primary_key=True, index=True)
    machine_id: int = Column(Integer, ForeignKey('machines.id'), nullable=False)
    alert_type: str = Column(String(64), nullable=False)
    level: str = Column(String(16), nullable=False, server_default='INFO', index=True)
    state: str = Column(String(16), nullable=False, server_default='ACTIVE', index=True)
    message: str = Column(String(512), nullable=False)
    expires_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True, index=True)
    resolved_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    machine = relationship('Machine', back_populates='alerts')
