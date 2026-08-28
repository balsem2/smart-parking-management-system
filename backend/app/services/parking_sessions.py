from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.parking_session import ParkingSession
from app.models.parking_spot import ParkingSpot
from app.models.payment import Payment
from app.services.billing import calculate_parking_fee
from app.services.monitoring import log_event


def complete_parking_session(db: Session, session: ParkingSession) -> ParkingSession:
    """Close a session, free its spot, and create its invoice exactly once."""
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
