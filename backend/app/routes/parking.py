from datetime import datetime, timezone
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.authorization import require_roles
from app.models.parking_session import ParkingSession
from app.models.parking_spot import ParkingSpot
from app.models.payment import Payment
from app.models.vehicle import Vehicle
from app.services.billing import calculate_parking_fee
from app.services.monitoring import (
    create_alert,
    log_event,
)
from app.services.realtime import publish_dashboard_event
from app.services.parking_spots import VALID_SPOT_STATUSES

router = APIRouter(tags=["parking"])


def normalize_plate(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def complete_parking_session(db: Session, session: ParkingSession) -> ParkingSession:
    """Close a session, release its spot, and create its payment once."""
    if session.status == "COMPLETED":
        raise HTTPException(status_code=400, detail="Parking session already completed")

    now = datetime.now(timezone.utc)
    entry = session.entry_time
    entry = entry.replace(tzinfo=timezone.utc) if entry.tzinfo is None else entry
    session.exit_time = now
    session.duration = max(0, int((now - entry).total_seconds() / 60))
    session.amount = calculate_parking_fee(session.duration)
    session.status = "COMPLETED"

    spot = db.query(ParkingSpot).filter(ParkingSpot.id == session.parking_spot_id).first()
    if spot:
        spot.status = "FREE"
    if not db.query(Payment).filter(Payment.parking_session_id == session.id).first():
        db.add(Payment(parking_session_id=session.id, amount=session.amount, status="PENDING"))
    log_event(db, "VEHICLE_EXITED", "Vehicle exited the parking", vehicle_id=session.vehicle_id, parking_session_id=session.id)
    db.commit()
    db.refresh(session)
    return session

@router.post("/parking-spots")
def create_parking_spot(spot: dict, db: Session = Depends(get_db), current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN"))):
    number = str(spot.get("number", "")).strip().upper()
    zone = str(spot.get("zone", "")).strip().upper()
    floor = str(spot.get("floor", "")).strip() or None
    status = str(spot.get("status", "FREE")).strip().upper()
    if not number or not zone:
        raise HTTPException(status_code=422, detail="Spot number and zone are required")
    if status not in VALID_SPOT_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid parking spot status")
    if db.query(ParkingSpot).filter(ParkingSpot.number == number).first():
        raise HTTPException(status_code=409, detail="A parking spot with this number already exists")

    result = ParkingSpot(number=number, zone=zone, floor=floor, status=status, vehicle_id=spot.get("vehicle_id"))
    db.add(result)
    db.commit()
    db.refresh(result)
    return result
@router.get("/parking-spots")
def get_parking_spots(db: Session = Depends(get_db), current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR", "SECURITY", "USER"))): return db.query(ParkingSpot).all()
@router.put("/parking-spots/{spot_id}/status")
async def update_spot_status(
    spot_id: int,
    data: dict,
    db: Session = Depends(get_db)
    , current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR"))
):
    spot = db.query(ParkingSpot).filter(
        ParkingSpot.id == spot_id
    ).first()

    if not spot:
        raise HTTPException(
            status_code=404,
            detail="Parking spot not found"
        )

    new_status = str(data.get("status", "")).strip().upper()
    if new_status not in VALID_SPOT_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid parking spot status")

    spot.status = new_status

    db.commit()
    db.refresh(spot)

    await publish_dashboard_event({
        "type": "spot_updated",
        "spot_id": spot.id,
        "status": spot.status
    })

    return {
        "message": "Parking spot status updated successfully",
        "id": spot.id,
        "number": spot.number,
        "status": spot.status
    }
@router.post("/parking-sessions")
async def create_parking_session(session: dict, db: Session = Depends(get_db), current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR", "SECURITY"))):
    vehicle = db.query(Vehicle).filter(Vehicle.id == session["vehicle_id"]).first()
    if not vehicle: raise HTTPException(status_code=404, detail="Vehicle not found")
    if vehicle.status == "BLACKLISTED":
        log_event(db, "ACCESS_DENIED", "Blacklisted vehicle was denied entry", vehicle_id=vehicle.id); create_alert(db, "BLACKLISTED_VEHICLE", "Blacklisted vehicle attempted to enter the parking", "CRITICAL", vehicle_id=vehicle.id); db.commit(); raise HTTPException(status_code=403, detail="Blacklisted vehicle cannot enter")
    spot_id = session.get("parking_spot_id"); spot = db.query(ParkingSpot).filter(ParkingSpot.id == spot_id).first() if spot_id else None
    if not spot: raise HTTPException(status_code=404 if spot_id else 400, detail="Parking spot not found" if spot_id else "Parking spot is required")
    if spot.status != "FREE": raise HTTPException(status_code=400, detail="Parking spot is not available")
    if db.query(ParkingSession).filter(ParkingSession.vehicle_id == vehicle.id, ParkingSession.status == "ACTIVE").first(): raise HTTPException(status_code=400, detail="Vehicle already has an active session")
    result = ParkingSession(vehicle_id=vehicle.id, parking_spot_id=spot.id, status="ACTIVE", amount=0); db.add(result); spot.status = "OCCUPIED"; db.flush(); log_event(db, "VEHICLE_ENTERED", "Vehicle entered the parking", vehicle_id=vehicle.id, parking_session_id=result.id); db.commit(); db.refresh(result)
    await publish_dashboard_event({"type": "spot_updated", "spot_id": spot.id, "status": "OCCUPIED", "vehicle_id": vehicle.id, "parking_session_id": result.id})
    return result


@router.post("/parking-entries/by-plate")
async def create_entry_by_plate(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR", "SECURITY")),
):
    plate_text = str(data.get("plate_text", "")).strip()
    spot_id = data.get("parking_spot_id")
    if not plate_text:
        raise HTTPException(status_code=422, detail="plate_text is required")
    if not isinstance(spot_id, int):
        raise HTTPException(status_code=422, detail="parking_spot_id must be an integer")

    normalized_plate = normalize_plate(plate_text)
    vehicle = next(
        (item for item in db.query(Vehicle).all() if normalize_plate(item.plate_number) == normalized_plate),
        None,
    )
    if not vehicle:
        # Camera entry is intentionally frictionless: a first-time vehicle is
        # kept as a visitor and can be managed later from the Vehicles screen.
        vehicle = Vehicle(plate_number=normalized_plate, type="car", status="VISITOR")
        db.add(vehicle)
        db.flush()
        log_event(
            db,
            "VISITOR_AUTO_REGISTERED",
            f"Vehicle was automatically registered from plate recognition: {plate_text}",
            vehicle_id=vehicle.id,
        )
    if vehicle.status == "BLACKLISTED":
        log_event(db, "ACCESS_DENIED", "Blacklisted vehicle was denied entry", vehicle_id=vehicle.id)
        create_alert(db, "BLACKLISTED_VEHICLE", "Blacklisted vehicle attempted to enter the parking", "CRITICAL", vehicle_id=vehicle.id)
        db.commit()
        raise HTTPException(status_code=403, detail="Blacklisted vehicle cannot enter")

    spot = db.query(ParkingSpot).filter(ParkingSpot.id == spot_id).first()
    if not spot:
        raise HTTPException(status_code=404, detail="Parking spot not found")
    if spot.status != "FREE":
        raise HTTPException(status_code=400, detail="Parking spot is not available")
    if db.query(ParkingSession).filter(ParkingSession.vehicle_id == vehicle.id, ParkingSession.status == "ACTIVE").first():
        raise HTTPException(status_code=400, detail="Vehicle already has an active session")

    result = ParkingSession(vehicle_id=vehicle.id, parking_spot_id=spot.id, status="ACTIVE", amount=0)
    db.add(result)
    spot.status = "OCCUPIED"
    db.flush()
    log_event(db, "VEHICLE_ENTERED", "Vehicle entered through plate recognition", vehicle_id=vehicle.id, parking_session_id=result.id)
    db.commit()
    db.refresh(result)
    await publish_dashboard_event({
        "type": "plate_entry_registered",
        "plate_text": plate_text,
        "vehicle_id": vehicle.id,
        "spot_id": spot.id,
        "parking_session_id": result.id,
        "status": "OCCUPIED",
    })
    return {
        "message": "Vehicle entry registered",
        "plate_text": plate_text,
        "vehicle": vehicle,
        "session": result,
    }


@router.post("/parking-exits/by-plate")
async def create_exit_by_plate(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR", "SECURITY")),
):
    plate_text = str(data.get("plate_text", "")).strip()
    if not plate_text:
        raise HTTPException(status_code=422, detail="plate_text is required")

    normalized_plate = normalize_plate(plate_text)
    vehicle = next(
        (item for item in db.query(Vehicle).all() if normalize_plate(item.plate_number) == normalized_plate),
        None,
    )
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    session = db.query(ParkingSession).filter(
        ParkingSession.vehicle_id == vehicle.id,
        ParkingSession.status == "ACTIVE",
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="No active parking session found for this vehicle")

    result = complete_parking_session(db, session)
    await publish_dashboard_event({
        "type": "plate_exit_registered",
        "plate_text": plate_text,
        "vehicle_id": vehicle.id,
        "spot_id": result.parking_spot_id,
        "parking_session_id": result.id,
        "status": "FREE",
    })
    return {
        "message": "Vehicle exit registered",
        "plate_text": plate_text,
        "vehicle": vehicle,
        "session": result,
    }
@router.get("/parking-sessions")
def get_parking_sessions(db: Session = Depends(get_db), current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR", "SECURITY"))): return db.query(ParkingSession).all()

@router.get("/my-parking-sessions")
def get_my_parking_sessions(db: Session = Depends(get_db), current_user=Depends(require_roles("USER"))):
    vehicle_ids = db.query(Vehicle.id).filter(Vehicle.user_id == current_user.id)
    sessions = db.query(ParkingSession).filter(ParkingSession.vehicle_id.in_(vehicle_ids)).order_by(ParkingSession.entry_time.desc()).all()
    now = datetime.now(timezone.utc)
    response = []
    for item in sessions:
        entry = item.entry_time.replace(tzinfo=timezone.utc) if item.entry_time.tzinfo is None else item.entry_time
        duration = item.duration if item.status == "COMPLETED" else max(0, int((now - entry).total_seconds() / 60))
        response.append({
            "id": item.id,
            "vehicle_id": item.vehicle_id,
            "parking_spot_id": item.parking_spot_id,
            "entry_time": item.entry_time,
            "status": item.status,
            "duration_minutes": duration,
            "amount": item.amount if item.status == "COMPLETED" else calculate_parking_fee(duration),
        })
    return response
@router.post("/parking-sessions/{session_id}/exit")
async def exit_parking_session(session_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR", "SECURITY"))):
    result = db.query(ParkingSession).filter(ParkingSession.id == session_id).first()
    if not result: raise HTTPException(status_code=404, detail="Parking session not found")
    result = complete_parking_session(db, result)
    await publish_dashboard_event({"type": "spot_updated", "spot_id": result.parking_spot_id, "status": "FREE", "vehicle_id": result.vehicle_id, "parking_session_id": result.id})
    return result
