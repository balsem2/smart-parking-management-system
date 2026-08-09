from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import AlertSeverity, ReservationStatus, SessionStatus, SpotStatus, VehicleStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class VehicleCreate(BaseModel):
    plate_number: str = Field(min_length=2, max_length=32)
    owner_name: str = Field(min_length=2, max_length=120)
    owner_phone: str | None = None
    type: str = "CAR"
    brand: str | None = None
    model: str | None = None
    color: str | None = None
    status: VehicleStatus = VehicleStatus.VISITOR
    subscription_expires_at: datetime | None = None

    @field_validator("plate_number")
    @classmethod
    def normalize_plate(cls, value: str) -> str:
        return "".join(value.upper().split())


class VehicleUpdate(BaseModel):
    owner_name: str | None = None
    owner_phone: str | None = None
    brand: str | None = None
    model: str | None = None
    color: str | None = None
    status: VehicleStatus | None = None
    subscription_expires_at: datetime | None = None


class VehicleRead(VehicleCreate, ORMModel):
    id: int
    created_at: datetime


class SpotCreate(BaseModel):
    number: str
    zone: str
    floor: int = 0


class SpotRead(SpotCreate, ORMModel):
    id: int
    status: SpotStatus
    vehicle_id: int | None


class ReservationCreate(BaseModel):
    vehicle_id: int
    start_time: datetime
    end_time: datetime
    zone: str | None = None


class ReservationRead(ORMModel):
    id: int
    vehicle_id: int
    spot_id: int
    start_time: datetime
    end_time: datetime
    status: ReservationStatus
    created_at: datetime


class AccessRequest(BaseModel):
    plate_number: str
    event_type: str = Field(pattern="^(ENTRY|EXIT)$")
    gate: str = "Gate A"
    confidence: float | None = Field(default=None, ge=0, le=1)
    image_url: str | None = None

    @field_validator("plate_number")
    @classmethod
    def normalize_plate(cls, value: str) -> str:
        return "".join(value.upper().split())


class AccessResponse(BaseModel):
    event_id: int
    decision: str
    reason: str
    session_id: int | None = None
    spot_number: str | None = None
    amount: float | None = None


class SessionRead(ORMModel):
    id: int
    vehicle_id: int
    spot_id: int
    entry_time: datetime
    exit_time: datetime | None
    duration_minutes: int | None
    amount: float | None
    payment_status: str
    status: SessionStatus


class EventRead(ORMModel):
    id: int
    plate_number: str
    vehicle_id: int | None
    event_type: str
    gate: str
    decision: str
    reason: str
    confidence: float | None
    image_url: str | None
    created_at: datetime


class AlertRead(ORMModel):
    id: int
    type: str
    severity: AlertSeverity
    message: str
    acknowledged_at: datetime | None
    created_at: datetime
