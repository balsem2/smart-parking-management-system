"""Seed two realistic alerts for a SmartPark product demonstration.

Run this script only in a demo/development database.  It is idempotent, so it
can safely be run again before recording a demo.
"""

from datetime import datetime, timedelta, timezone

import app.models  # noqa: F401
from app.core.database import SessionLocal
from app.models.alert import Alert
from app.models.parking_session import ParkingSession
from app.models.parking_spot import ParkingSpot
from app.models.vehicle import Vehicle


BLACKLISTED_PLATE = "DEMO-BLACK-01"
OVERTIME_PLATE = "DEMO-OVERTIME-01"
SPOT_NUMBER = "DEMO-A-01"


def get_or_create_vehicle(db, plate_number, status):
    vehicle = db.query(Vehicle).filter(Vehicle.plate_number == plate_number).first()
    if not vehicle:
        vehicle = Vehicle(
            plate_number=plate_number,
            owner_name="Demo Driver",
            type="car",
            status=status,
        )
        db.add(vehicle)
        db.flush()
    else:
        vehicle.status = status
    return vehicle


def main():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        blacklisted_vehicle = get_or_create_vehicle(db, BLACKLISTED_PLATE, "BLACKLISTED")
        overtime_vehicle = get_or_create_vehicle(db, OVERTIME_PLATE, "AUTHORIZED")

        spot = db.query(ParkingSpot).filter(ParkingSpot.number == SPOT_NUMBER).first()
        if not spot:
            spot = ParkingSpot(number=SPOT_NUMBER, zone="DEMO", floor="Ground", status="OCCUPIED")
            db.add(spot)
            db.flush()
        else:
            spot.status = "OCCUPIED"

        session = (
            db.query(ParkingSession)
            .filter(ParkingSession.vehicle_id == overtime_vehicle.id, ParkingSession.status == "ACTIVE")
            .first()
        )
        if not session:
            session = ParkingSession(
                vehicle_id=overtime_vehicle.id,
                parking_spot_id=spot.id,
                entry_time=now - timedelta(hours=2),
                status="ACTIVE",
                amount=0,
            )
            db.add(session)
            db.flush()

        examples = (
            ("BLACKLISTED_VEHICLE", blacklisted_vehicle.id, None,
             f"Blacklisted vehicle {BLACKLISTED_PLATE} attempted to enter the parking.", "CRITICAL"),
            ("RESERVATION_TIME_EXCEEDED", overtime_vehicle.id, session.id,
             f"Vehicle {OVERTIME_PLATE} is still parked after its paid reservation ended.", "WARNING"),
        )
        for alert_type, vehicle_id, session_id, message, severity in examples:
            exists = db.query(Alert).filter(
                Alert.alert_type == alert_type,
                Alert.vehicle_id == vehicle_id,
                Alert.parking_session_id == session_id,
                Alert.status == "ACTIVE",
            ).first()
            if not exists:
                db.add(Alert(
                    alert_type=alert_type,
                    vehicle_id=vehicle_id,
                    parking_session_id=session_id,
                    message=message,
                    severity=severity,
                    status="ACTIVE",
                ))

        db.commit()
        print("Demo alerts are ready: BLACKLISTED_VEHICLE and RESERVATION_TIME_EXCEEDED")
    finally:
        db.close()


if __name__ == "__main__":
    main()
