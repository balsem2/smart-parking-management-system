from datetime import datetime, timezone

from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Text


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="WARNING")
    message = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE")
    vehicle_id = Column(Integer, nullable=True)
    parking_session_id = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
