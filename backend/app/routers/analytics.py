from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import AccessEvent, Alert, ParkingSession, ParkingSpot, SessionStatus, SpotStatus

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    capacity = db.scalar(select(func.count(ParkingSpot.id))) or 0
    occupied = db.scalar(select(func.count(ParkingSpot.id)).where(ParkingSpot.status == SpotStatus.OCCUPIED)) or 0
    vehicles_today = db.scalar(select(func.count(AccessEvent.id)).where(
        AccessEvent.created_at >= start, AccessEvent.event_type == "ENTRY", AccessEvent.decision == "ALLOW"
    )) or 0
    revenue_today = db.scalar(select(func.coalesce(func.sum(ParkingSession.amount), 0)).where(
        ParkingSession.exit_time >= start, ParkingSession.status == SessionStatus.COMPLETED
    )) or 0
    alerts = db.scalar(select(func.count(Alert.id)).where(Alert.acknowledged_at.is_(None))) or 0
    denied = db.scalar(select(func.count(AccessEvent.id)).where(
        AccessEvent.created_at >= start, AccessEvent.decision == "DENY"
    )) or 0
    return {
        "vehicles_today": vehicles_today,
        "capacity": capacity,
        "occupied": occupied,
        "available": max(0, capacity - occupied),
        "occupancy_rate": round(occupied / capacity * 100, 1) if capacity else 0,
        "revenue_today": round(float(revenue_today), 2),
        "currency": "TND",
        "active_alerts": alerts,
        "denied_today": denied,
    }
