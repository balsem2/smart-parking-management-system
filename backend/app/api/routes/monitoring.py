from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from models.alert import Alert
from models.event import Event
from services.monitoring import create_alert

router = APIRouter(tags=["monitoring"])
ALERT_TYPES = {"BLACKLISTED_VEHICLE", "PARKING_FULL", "CAMERA_OFFLINE", "UNAUTHORIZED_ACCESS", "LONG_STAY"}

@router.get("/events")
def get_events(db: Session = Depends(get_db)): return db.query(Event).order_by(Event.created_at.desc()).all()
@router.get("/alerts")
def get_alerts(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Alert)
    return query.filter(Alert.status == status.upper()).order_by(Alert.created_at.desc()).all() if status else query.order_by(Alert.created_at.desc()).all()
@router.post("/alerts")
def create_manual_alert(alert: dict, db: Session = Depends(get_db)):
    alert_type, message = alert.get("alert_type", "").upper(), alert.get("message", "").strip()
    if alert_type not in ALERT_TYPES or not message: raise HTTPException(status_code=422, detail="Invalid alert type or missing message")
    result = create_alert(db, alert_type, message, alert.get("severity", "WARNING").upper(), vehicle_id=alert.get("vehicle_id"), parking_session_id=alert.get("parking_session_id")); db.commit(); db.refresh(result); return result
@router.put("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert: raise HTTPException(status_code=404, detail="Alert not found")
    alert.status, alert.resolved_at = "RESOLVED", datetime.now(timezone.utc); db.commit(); db.refresh(alert); return alert
