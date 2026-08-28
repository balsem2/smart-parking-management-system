from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.event import Event
from app.models.parking_session import ParkingSession
from app.models.reservation import Reservation


IMPORTANT_ALERT_TYPES = ("BLACKLISTED_VEHICLE", "RESERVATION_TIME_EXCEEDED")

def log_event(db: Session, event_type: str, description: str, **ids):
    event = Event(event_type=event_type, description=description, **ids); db.add(event); return event
def create_alert(db: Session, alert_type: str, message: str, severity="WARNING", **ids):
    alert = Alert(alert_type=alert_type, message=message, severity=severity, **ids); db.add(alert); return alert


def create_reservation_time_exceeded_alerts(db: Session) -> list[Alert]:
    """Create one active alert for each car still parked after its paid booking ends."""
    now = datetime.now(timezone.utc)
    created_alerts: list[Alert] = []
    active_sessions = db.query(ParkingSession).filter(ParkingSession.status == "ACTIVE").all()

    for session in active_sessions:
        reservation = (
            db.query(Reservation)
            .filter(
                Reservation.vehicle_id == session.vehicle_id,
                Reservation.parking_spot_id == session.parking_spot_id,
                Reservation.status == "CONFIRMED",
                Reservation.end_time < now,
                Reservation.end_time >= session.entry_time,
            )
            .order_by(Reservation.end_time.desc())
            .first()
        )
        if not reservation:
            continue

        existing_alert = db.query(Alert).filter(
            Alert.alert_type == "RESERVATION_TIME_EXCEEDED",
            Alert.parking_session_id == session.id,
            Alert.status == "ACTIVE",
        ).first()
        if not existing_alert:
            alert = create_alert(
                db,
                "RESERVATION_TIME_EXCEEDED",
                "Vehicle is still parked after its paid reservation ended.",
                "WARNING",
                vehicle_id=session.vehicle_id,
                parking_session_id=session.id,
            )
            created_alerts.append(alert)
    return created_alerts
