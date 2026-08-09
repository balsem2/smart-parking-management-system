from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import (
    AccessEvent,
    Alert,
    AlertSeverity,
    ParkingSession,
    ParkingSpot,
    SessionStatus,
    SpotStatus,
    Vehicle,
)
from app.realtime import manager
from app.schemas import AccessRequest, AccessResponse, EventRead
from app.services.access_service import access_decision
from app.services.billing_service import calculate_amount

router = APIRouter(prefix="/events", tags=["access events"])


@router.get("", response_model=list[EventRead])
def list_events(limit: int = 100, db: Session = Depends(get_db)):
    return db.scalars(select(AccessEvent).order_by(AccessEvent.created_at.desc()).limit(min(limit, 500))).all()


@router.post("/access", response_model=AccessResponse)
async def process_access(payload: AccessRequest, db: Session = Depends(get_db)):
    vehicle = db.scalar(select(Vehicle).where(Vehicle.plate_number == payload.plate_number))
    allowed, reason = access_decision(vehicle)
    session = None
    spot = None
    amount = None

    if allowed and payload.event_type == "ENTRY":
        existing = db.scalar(select(ParkingSession).where(
            ParkingSession.vehicle_id == vehicle.id, ParkingSession.status == SessionStatus.ACTIVE
        ))
        if existing:
            allowed, reason = False, "SESSION_ALREADY_ACTIVE"
        else:
            spot = db.scalar(select(ParkingSpot).where(ParkingSpot.status == SpotStatus.FREE).order_by(ParkingSpot.number).limit(1))
            if not spot:
                allowed, reason = False, "PARKING_FULL"
            else:
                spot.status = SpotStatus.OCCUPIED
                spot.vehicle_id = vehicle.id
                session = ParkingSession(vehicle_id=vehicle.id, spot_id=spot.id)
                db.add(session)

    elif allowed and payload.event_type == "EXIT":
        session = db.scalar(select(ParkingSession).where(
            ParkingSession.vehicle_id == vehicle.id, ParkingSession.status == SessionStatus.ACTIVE
        ))
        if not session:
            allowed, reason = False, "NO_ACTIVE_SESSION"
        else:
            now = datetime.now(timezone.utc)
            entry = session.entry_time
            if entry.tzinfo is None:
                entry = entry.replace(tzinfo=timezone.utc)
            session.exit_time = now
            session.duration_minutes = max(1, int((now - entry).total_seconds() / 60))
            session.amount = calculate_amount(session.duration_minutes)
            session.status = SessionStatus.COMPLETED
            amount = session.amount
            spot = db.get(ParkingSpot, session.spot_id)
            spot.status = SpotStatus.FREE
            spot.vehicle_id = None

    event = AccessEvent(
        plate_number=payload.plate_number,
        vehicle_id=vehicle.id if vehicle else None,
        event_type=payload.event_type,
        gate=payload.gate,
        decision="ALLOW" if allowed else "DENY",
        reason=reason,
        confidence=payload.confidence,
        image_url=payload.image_url,
    )
    db.add(event)
    if not allowed and reason in {"BLACKLISTED", "UNKNOWN_VEHICLE", "PARKING_FULL"}:
        db.add(Alert(
            type=reason,
            severity=AlertSeverity.CRITICAL if reason == "BLACKLISTED" else AlertSeverity.WARNING,
            message=f"{reason.replace('_', ' ').title()}: {payload.plate_number}",
        ))
    db.commit()
    db.refresh(event)
    if session:
        db.refresh(session)

    response = AccessResponse(
        event_id=event.id,
        decision=event.decision,
        reason=reason,
        session_id=session.id if session else None,
        spot_number=spot.number if spot else None,
        amount=amount,
    )
    await manager.broadcast({"type": "ACCESS_EVENT", "data": response.model_dump()})
    return response


@router.websocket("/ws")
async def event_stream(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
