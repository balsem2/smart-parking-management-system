from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from models.parking_session import ParkingSession
from models.parking_spot import ParkingSpot
from models.vehicle import Vehicle
from services.billing import calculate_parking_fee
from services.monitoring import create_alert, create_parking_full_alert_if_needed, log_event, resolve_parking_full_alerts

router = APIRouter(tags=["parking"])

@router.post("/parking-spots")
def create_parking_spot(spot: dict, db: Session = Depends(get_db)):
    result = ParkingSpot(number=spot["number"], zone=spot["zone"], floor=spot.get("floor"), status=spot.get("status", "FREE"), vehicle_id=spot.get("vehicle_id")); db.add(result); db.commit(); db.refresh(result); return result
@router.get("/parking-spots")
def get_parking_spots(db: Session = Depends(get_db)): return db.query(ParkingSpot).all()
@router.put("/parking-spots/{spot_id}/status")
def update_spot_status(spot_id: int, data: dict, db: Session = Depends(get_db)):
    spot = db.query(ParkingSpot).filter(ParkingSpot.id == spot_id).first()
    if not spot: return {"error": "Parking spot not found"}
    spot.status = data["status"]; db.commit(); db.refresh(spot); return {"message": "Parking spot status updated successfully", "id": spot.id, "number": spot.number, "status": spot.status}
@router.post("/parking-sessions")
def create_parking_session(session: dict, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == session["vehicle_id"]).first()
    if not vehicle: raise HTTPException(status_code=404, detail="Vehicle not found")
    if vehicle.status == "BLACKLISTED":
        log_event(db, "ACCESS_DENIED", "Blacklisted vehicle was denied entry", vehicle_id=vehicle.id); create_alert(db, "BLACKLISTED_VEHICLE", "Blacklisted vehicle attempted to enter the parking", "CRITICAL", vehicle_id=vehicle.id); db.commit(); raise HTTPException(status_code=403, detail="Blacklisted vehicle cannot enter")
    spot_id = session.get("parking_spot_id"); spot = db.query(ParkingSpot).filter(ParkingSpot.id == spot_id).first() if spot_id else None
    if not spot: raise HTTPException(status_code=404 if spot_id else 400, detail="Parking spot not found" if spot_id else "Parking spot is required")
    if spot.status != "FREE": raise HTTPException(status_code=400, detail="Parking spot is not available")
    if db.query(ParkingSession).filter(ParkingSession.vehicle_id == vehicle.id, ParkingSession.status == "ACTIVE").first(): raise HTTPException(status_code=400, detail="Vehicle already has an active session")
    result = ParkingSession(vehicle_id=vehicle.id, parking_spot_id=spot.id, status="ACTIVE", amount=0); db.add(result); spot.status = "OCCUPIED"; db.flush(); log_event(db, "VEHICLE_ENTERED", "Vehicle entered the parking", vehicle_id=vehicle.id, parking_session_id=result.id); create_parking_full_alert_if_needed(db); db.commit(); db.refresh(result); return result
@router.get("/parking-sessions")
def get_parking_sessions(db: Session = Depends(get_db)): return db.query(ParkingSession).all()
@router.post("/parking-sessions/{session_id}/exit")
def exit_parking_session(session_id: int, db: Session = Depends(get_db)):
    result = db.query(ParkingSession).filter(ParkingSession.id == session_id).first()
    if not result: raise HTTPException(status_code=404, detail="Parking session not found")
    if result.status == "COMPLETED": raise HTTPException(status_code=400, detail="Parking session already completed")
    now, entry = datetime.now(timezone.utc), result.entry_time; entry = entry.replace(tzinfo=timezone.utc) if entry.tzinfo is None else entry; result.exit_time = now; result.duration = int((now-entry).total_seconds()/60); result.amount = calculate_parking_fee(result.duration); result.status = "COMPLETED"
    spot = db.query(ParkingSpot).filter(ParkingSpot.id == result.parking_spot_id).first()
    if spot: spot.status = "FREE"
    log_event(db, "VEHICLE_EXITED", "Vehicle exited the parking", vehicle_id=result.vehicle_id, parking_session_id=result.id)
    if result.duration >= 480: create_alert(db, "LONG_STAY", "Vehicle exceeded the configured maximum parking duration", vehicle_id=result.vehicle_id, parking_session_id=result.id)
    resolve_parking_full_alerts(db); db.commit(); db.refresh(result); return result
