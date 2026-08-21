from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models
from app.core.database import Base
from app.models.parking_spot import ParkingSpot
from app.services.parking_spots import seed_default_parking_spots


def test_default_parking_spots_are_seeded_once_without_overwriting_existing_data():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    db.add(ParkingSpot(number="A-01", zone="Custom", floor="Roof", status="MAINTENANCE"))
    db.commit()

    assert seed_default_parking_spots(db) == 39
    assert db.query(ParkingSpot).count() == 40
    assert db.query(ParkingSpot).filter_by(number="A-01").one().status == "MAINTENANCE"
    assert seed_default_parking_spots(db) == 0

    db.close()
