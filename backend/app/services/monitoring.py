from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.alert import Alert
from models.event import Event
from models.parking_spot import ParkingSpot

def log_event(db: Session, event_type: str, description: str, **ids):
    event = Event(event_type=event_type, description=description, **ids); db.add(event); return event
def create_alert(db: Session, alert_type: str, message: str, severity="WARNING", **ids):
    alert = Alert(alert_type=alert_type, message=message, severity=severity, **ids); db.add(alert); return alert
def create_parking_full_alert_if_needed(db: Session):
    if not db.query(ParkingSpot).filter(ParkingSpot.status == "FREE").count() and not db.query(Alert).filter(Alert.alert_type == "PARKING_FULL", Alert.status == "ACTIVE").first(): create_alert(db, "PARKING_FULL", "No parking spots are currently available")
def resolve_parking_full_alerts(db: Session):
    for alert in db.query(Alert).filter(Alert.alert_type == "PARKING_FULL", Alert.status == "ACTIVE").all(): alert.status, alert.resolved_at = "RESOLVED", datetime.now(timezone.utc)
