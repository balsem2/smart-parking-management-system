from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from core.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)

    plate_number = Column(
        String(20),
        unique=True,
        nullable=False,
        index=True
    )

    owner_name = Column(String(100), nullable=True)
    owner_phone = Column(String(20), nullable=True)

    type = Column(String(30), nullable=True)
    brand = Column(String(50), nullable=True)
    model = Column(String(50), nullable=True)
    color = Column(String(30), nullable=True)

    status = Column(
        String(30),
        nullable=False,
        default="VISITOR"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )