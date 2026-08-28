from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.core.database import Base
from app.models.parking_session import ParkingSession
from app.models.parking_spot import ParkingSpot
from app.models.payment import Payment
from app.models.vehicle import Vehicle
from app.services.parking_sessions import complete_parking_session


def test_exit_completes_session_releases_spot_and_creates_payment():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    spot = ParkingSpot(number="A-01", zone="A", status="OCCUPIED")
    vehicle = Vehicle(plate_number="EXIT-001", status="AUTHORIZED")
    db.add_all((spot, vehicle))
    db.flush()
    session = ParkingSession(
        vehicle_id=vehicle.id,
        parking_spot_id=spot.id,
        entry_time=datetime.now(timezone.utc) - timedelta(hours=2),
        status="ACTIVE",
    )
    db.add(session)
    db.commit()

    completed = complete_parking_session(db, session)

    assert completed.status == "COMPLETED"
    assert completed.duration >= 120
    assert db.query(ParkingSpot).filter_by(id=spot.id).one().status == "FREE"
    payment = db.query(Payment).filter_by(parking_session_id=session.id).one()
    assert payment.status == "PENDING"
    assert payment.amount == completed.amount

    db.close()
