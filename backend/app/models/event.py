from datetime import datetime, timezone

from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Text


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=False)
    vehicle_id = Column(Integer, nullable=True)
    parking_session_id = Column(Integer, nullable=True)
    reservation_id = Column(Integer, nullable=True)
    payment_id = Column(Integer, nullable=True)
    user_id = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
