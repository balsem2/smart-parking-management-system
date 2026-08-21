from datetime import datetime, timezone
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.authorization import require_roles
from app.models.parking_spot import ParkingSpot
from app.models.payment import Payment
from app.models.reservation import Reservation
from app.models.user import User
from app.models.vehicle import Vehicle
from app.services.monitoring import log_event

router = APIRouter(tags=["reservations"])
ACTIVE_STATUSES = ("PENDING", "CONFIRMED")
STATUSES = (*ACTIVE_STATUSES, "CANCELLED", "COMPLETED")


def parse_datetime(value: str | datetime, field_name: str) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"{field_name} must use ISO 8601 datetime format") from exc
    else:
        raise HTTPException(status_code=422, detail=f"{field_name} must use ISO 8601 datetime format")
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result


def ensure_available(db: Session, spot_id: int, start: datetime, end: datetime, exclude_id: int | None = None) -> None:
    if start >= end:
        raise HTTPException(status_code=422, detail="end_time must be after start_time")
    query = db.query(Reservation).filter(Reservation.parking_spot_id == spot_id, Reservation.status.in_(ACTIVE_STATUSES), Reservation.start_time < end, Reservation.end_time > start)
    if exclude_id is not None:
        query = query.filter(Reservation.id != exclude_id)
    if query.first():
        raise HTTPException(status_code=409, detail="Parking spot is already reserved during this period")


@router.post("/reservations")
def create_reservation(data: dict, db: Session = Depends(get_db), current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR", "USER"))):
    owner_id = current_user.id if current_user.role == "USER" else data["user_id"]
    user = db.query(User).filter(User.id == owner_id).first()
    vehicle = db.query(Vehicle).filter(Vehicle.id == data.get("vehicle_id")).first() if data.get("vehicle_id") else None
    if current_user.role == "USER" and not vehicle:
        plate_number = str(data.get("plate_number", "")).strip().upper()
        if not plate_number:
            raise HTTPException(status_code=422, detail="plate_number is required")
        normalized_plate = re.sub(r"[^A-Z0-9]", "", plate_number)
        vehicle = next((item for item in db.query(Vehicle).all() if re.sub(r"[^A-Z0-9]", "", item.plate_number.upper()) == normalized_plate), None)
        if vehicle and vehicle.user_id not in (None, current_user.id):
            raise HTTPException(status_code=409, detail="This plate belongs to another account")
        if not vehicle:
            vehicle = Vehicle(plate_number=plate_number, user_id=current_user.id, status="AUTHORIZED")
            db.add(vehicle)
            db.flush()
        elif vehicle.user_id is None:
            vehicle.user_id = current_user.id
    spot = db.query(ParkingSpot).filter(ParkingSpot.id == data["parking_spot_id"]).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    if not vehicle: raise HTTPException(status_code=404, detail="Vehicle not found")
    if not spot: raise HTTPException(status_code=404, detail="Parking spot not found")
    start, end = parse_datetime(data["start_time"], "start_time"), parse_datetime(data["end_time"], "end_time")
    ensure_available(db, spot.id, start, end)
    result = Reservation(user_id=user.id, vehicle_id=vehicle.id, parking_spot_id=spot.id, start_time=start, end_time=end, status="PENDING")
    db.add(result); db.flush()
    payment_method = str(data.get("payment_method", "CARD")).strip().upper()
    if payment_method not in {"CARD", "CASH"}:
        raise HTTPException(status_code=422, detail="payment_method must be CARD or CASH")
    duration_minutes = max(1, int((end - start).total_seconds() / 60))
    from app.services.billing import calculate_parking_fee
    payment = Payment(reservation_id=result.id, amount=calculate_parking_fee(duration_minutes), status="PENDING", payment_method=payment_method)
    db.add(payment)
    db.flush()
    log_event(db, "RESERVATION_CREATED", "Parking reservation awaiting payment", vehicle_id=vehicle.id, reservation_id=result.id, user_id=user.id)
    db.commit(); db.refresh(result); db.refresh(payment)
    return {"reservation": result, "payment": payment}


@router.get("/reservations")
def get_reservations(db: Session = Depends(get_db), current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR", "SECURITY", "USER"))):
    query = db.query(Reservation)
    return query.filter(Reservation.user_id == current_user.id).all() if current_user.role == "USER" else query.all()


@router.get("/reservations/{reservation_id}")
def get_reservation(reservation_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR", "SECURITY", "USER"))):
    result = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not result: raise HTTPException(status_code=404, detail="Reservation not found")
    return result


@router.put("/reservations/{reservation_id}")
def update_reservation(reservation_id: int, data: dict, db: Session = Depends(get_db), current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR", "USER"))):
    result = get_reservation(reservation_id, db)
    if current_user.role == "USER" and result.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only manage your own reservations")
    if result.status in ("CANCELLED", "COMPLETED"): raise HTTPException(status_code=400, detail="This reservation cannot be updated")
    user_id, vehicle_id, spot_id = data.get("user_id", result.user_id), data.get("vehicle_id", result.vehicle_id), data.get("parking_spot_id", result.parking_spot_id)
    start, end = parse_datetime(data.get("start_time", result.start_time), "start_time"), parse_datetime(data.get("end_time", result.end_time), "end_time")
    status = data.get("status", result.status).upper()
    if status not in STATUSES: raise HTTPException(status_code=422, detail="Invalid reservation status")
    if not db.query(User).filter(User.id == user_id).first(): raise HTTPException(status_code=404, detail="User not found")
    if not db.query(Vehicle).filter(Vehicle.id == vehicle_id).first(): raise HTTPException(status_code=404, detail="Vehicle not found")
    if not db.query(ParkingSpot).filter(ParkingSpot.id == spot_id).first(): raise HTTPException(status_code=404, detail="Parking spot not found")
    if status in ACTIVE_STATUSES: ensure_available(db, spot_id, start, end, result.id)
    result.user_id, result.vehicle_id, result.parking_spot_id, result.start_time, result.end_time, result.status = user_id, vehicle_id, spot_id, start, end, status
    db.commit(); db.refresh(result); return result


@router.delete("/reservations/{reservation_id}")
def delete_reservation(reservation_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR", "USER"))):
    result = get_reservation(reservation_id, db)
    if current_user.role == "USER" and result.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only manage your own reservations")
    db.delete(result); db.commit()
    return {"message": "Reservation deleted successfully"}
