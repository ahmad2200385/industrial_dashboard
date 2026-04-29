"""Sensor data model for machine telemetry."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.session import Base


class SensorData(Base):
    """Represents a single sensor reading from a machine.
    
    Attributes:
        id: Unique identifier
        machine_id: Reference to machine
        temperature: Temperature reading in Celsius
        status: Machine operational status
        production_count: Number of units produced
        timestamp: When the reading was taken
        created_at: When record was created in database
        machine: Related machine object
    """
    
    __tablename__ = 'sensor_data'

    id: int = Column(Integer, primary_key=True, index=True)
    machine_id: int = Column(Integer, ForeignKey('machines.id'), nullable=False, index=True)
    temperature: float = Column(Float, nullable=False)
    status: str = Column(String(32), nullable=False, index=True)
    production_count: int = Column(Integer, nullable=False)
    timestamp: datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    machine = relationship('Machine', back_populates='sensor_data')

    __table_args__ = (
        Index('ix_sensor_data_machine_timestamp', 'machine_id', 'timestamp'),
    )
