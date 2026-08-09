import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VehicleStatus(str, enum.Enum):
    AUTHORIZED = "AUTHORIZED"
    VISITOR = "VISITOR"
    VIP = "VIP"
    BLACKLISTED = "BLACKLISTED"
    EXPIRED = "EXPIRED"


class SpotStatus(str, enum.Enum):
    FREE = "FREE"
    OCCUPIED = "OCCUPIED"
    RESERVED = "RESERVED"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


class SessionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class ReservationStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class AlertSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[int] = mapped_column(primary_key=True)
    plate_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    owner_name: Mapped[str] = mapped_column(String(120))
    owner_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    type: Mapped[str] = mapped_column(String(32), default="CAR")
    brand: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[VehicleStatus] = mapped_column(Enum(VehicleStatus), default=VehicleStatus.VISITOR)
    subscription_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sessions: Mapped[list["ParkingSession"]] = relationship(back_populates="vehicle")


class ParkingSpot(Base):
    __tablename__ = "parking_spots"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    zone: Mapped[str] = mapped_column(String(20))
    floor: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[SpotStatus] = mapped_column(Enum(SpotStatus), default=SpotStatus.FREE)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)


class ParkingSession(Base):
    __tablename__ = "parking_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), index=True)
    spot_id: Mapped[int] = mapped_column(ForeignKey("parking_spots.id"))
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    payment_status: Mapped[str] = mapped_column(String(20), default="UNPAID")
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), default=SessionStatus.ACTIVE)
    vehicle: Mapped[Vehicle] = relationship(back_populates="sessions")
    spot: Mapped[ParkingSpot] = relationship()


class Reservation(Base):
    __tablename__ = "reservations"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    spot_id: Mapped[int] = mapped_column(ForeignKey("parking_spots.id"))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[ReservationStatus] = mapped_column(Enum(ReservationStatus), default=ReservationStatus.CONFIRMED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AccessEvent(Base):
    __tablename__ = "access_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    plate_number: Mapped[str] = mapped_column(String(32), index=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(16))
    gate: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(String(120))
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity))
    message: Mapped[str] = mapped_column(Text)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
