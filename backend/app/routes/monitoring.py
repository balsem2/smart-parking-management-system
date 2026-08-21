from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.authorization import require_roles
from app.models.alert import Alert
from app.models.event import Event
from app.services.monitoring import (
    IMPORTANT_ALERT_TYPES,
    create_alert,
    create_reservation_time_exceeded_alerts,
)

router = APIRouter(tags=["monitoring"])
ALERT_TYPES = set(IMPORTANT_ALERT_TYPES)

@router.get("/events")
def get_events(db: Session = Depends(get_db), current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN"))): return db.query(Event).order_by(Event.created_at.desc()).all()
@router.get("/alerts")
def get_alerts(status: str | None = None, db: Session = Depends(get_db), current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR", "SECURITY"))):
    create_reservation_time_exceeded_alerts(db)
    db.commit()
    query = db.query(Alert).filter(Alert.alert_type.in_(IMPORTANT_ALERT_TYPES))
    return query.filter(Alert.status == status.upper()).order_by(Alert.created_at.desc()).all() if status else query.order_by(Alert.created_at.desc()).all()
@router.post("/alerts")
def create_manual_alert(alert: dict, db: Session = Depends(get_db), current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "SECURITY"))):
    alert_type, message = alert.get("alert_type", "").upper(), alert.get("message", "").strip()
    if alert_type not in ALERT_TYPES or not message: raise HTTPException(status_code=422, detail="Invalid alert type or missing message")
    result = create_alert(db, alert_type, message, alert.get("severity", "WARNING").upper(), vehicle_id=alert.get("vehicle_id"), parking_session_id=alert.get("parking_session_id")); db.commit(); db.refresh(result); return result
@router.put("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "SECURITY"))):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert: raise HTTPException(status_code=404, detail="Alert not found")
    alert.status, alert.resolved_at = "RESOLVED", datetime.now(timezone.utc); db.commit(); db.refresh(alert); return alert
