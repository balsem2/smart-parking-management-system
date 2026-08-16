from core.database import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship


class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)

    parking_spot_id = Column(Integer, ForeignKey("parking_spots.id"), nullable=False)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    status = Column(String(30), nullable=False, default="PENDING")

    user = relationship("User")
    vehicle = relationship("Vehicle")
    parking_spot = relationship("ParkingSpot")
