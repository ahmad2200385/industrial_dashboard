"""Machine model for industrial equipment tracking."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.session import Base


class Machine(Base):
    """Represents an industrial machine in the system.
    
    Attributes:
        id: Unique identifier
        name: Machine name/identifier
        location: Physical location of the machine
        created_at: Timestamp when machine was added to system
        sensor_data: Related sensor readings
        alerts: Related alerts for this machine
    """
    
    __tablename__ = 'machines'

    id: int = Column(Integer, primary_key=True, index=True)
    name: str = Column(String(256), nullable=False)
    location: str = Column(String(256), nullable=False)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    sensor_data = relationship('SensorData', back_populates='machine', cascade='all, delete-orphan')
    alerts = relationship('Alert', back_populates='machine', cascade='all, delete-orphan')
