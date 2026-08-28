from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.core.database import Base
from app.models.alert import Alert
from app.models.parking_session import ParkingSession
from app.models.parking_spot import ParkingSpot
from app.models.reservation import Reservation
from app.models.user import User
from app.models.vehicle import Vehicle
from app.services.monitoring import create_reservation_time_exceeded_alerts


def test_reservation_overtime_alert_is_created_once():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    now = datetime.now(timezone.utc)
    user = User(username="customer", email="customer@example.com", role="USER", status="ACTIVE", is_active=True)
    spot = ParkingSpot(number="A-01", zone="A", status="OCCUPIED")
    db.add_all((user, spot))
    db.flush()
    vehicle = Vehicle(plate_number="TEST-001", user_id=user.id, status="AUTHORIZED")
    db.add(vehicle)
    db.flush()
    session = ParkingSession(vehicle_id=vehicle.id, parking_spot_id=spot.id, entry_time=now - timedelta(hours=2), status="ACTIVE")
    reservation = Reservation(user_id=user.id, vehicle_id=vehicle.id, parking_spot_id=spot.id, start_time=now - timedelta(hours=3), end_time=now - timedelta(minutes=1), status="CONFIRMED")
    db.add_all((session, reservation))
    db.commit()

    assert len(create_reservation_time_exceeded_alerts(db)) == 1
    db.commit()
    assert db.query(Alert).filter_by(alert_type="RESERVATION_TIME_EXCEEDED").count() == 1
    assert create_reservation_time_exceeded_alerts(db) == []

    db.close()
