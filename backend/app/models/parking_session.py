from sqlalchemy import Column, Integer, DateTime, String, Float
from datetime import datetime, timezone

from core.database import Base


class ParkingSession(Base):
    __tablename__ = "parking_sessions"

    id = Column(Integer, primary_key=True, index=True)

    vehicle_id = Column(Integer, nullable=False)

    parking_spot_id = Column(Integer, nullable=True)

    entry_time = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    exit_time = Column(
        DateTime(timezone=True),
        nullable=True
    )

    duration = Column(
        Integer,
        nullable=True
    )

    amount = Column(
        Float,
        default=0
    )

    status = Column(
        String(30),
        default="ACTIVE"
    )