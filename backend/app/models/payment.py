from datetime import datetime, timezone

from core.database import Base
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    parking_session_id = Column(
        Integer, ForeignKey("parking_sessions.id"), nullable=False, unique=True
    )
    amount = Column(Float, nullable=False)
    status = Column(String(30), nullable=False, default="PENDING")
    payment_method = Column(String(30), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    parking_session = relationship("ParkingSession")
