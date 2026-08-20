from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class ParkingSpot(Base):
    __tablename__ = "parking_spots"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(20), nullable=False, unique=True)
    zone = Column(String(50), nullable=False)
    floor = Column(String(20), nullable=True)
    status = Column(String(30), nullable=False, default="FREE")

    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)

    vehicle = relationship("Vehicle")
