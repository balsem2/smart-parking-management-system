from datetime import datetime, timezone

from core.database import Base
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship


class ParkingSession(Base):
    __tablename__ = "parking_sessions"

    id = Column(Integer, primary_key=True, index=True)

    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)

    parking_spot_id = Column(Integer, ForeignKey("parking_spots.id"), nullable=False)

    entry_time = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    exit_time = Column(DateTime(timezone=True), nullable=True)

    duration = Column(Integer, nullable=True)

    amount = Column(Float, default=0)

    status = Column(String(30), default="ACTIVE")

    vehicle = relationship("Vehicle")
    parking_spot = relationship("ParkingSpot")
