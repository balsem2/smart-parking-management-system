from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models
from app.core.database import Base
from app.models.parking_session import ParkingSession
from app.models.parking_spot import ParkingSpot
from app.models.payment import Payment
from app.models.reservation import Reservation
from app.models.user import User
from app.models.vehicle import Vehicle
from app.routes.users import create_user_record


def create_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session(), engine


def test_models_package_import_registers_all_tables():
    assert "users" in Base.metadata.tables
    assert "reservations" in Base.metadata.tables
    assert "parking_spots" in Base.metadata.tables


def test_public_user_registration_defaults_to_active_user():
    db, _ = create_session()

    result = create_user_record(
        {
            "username": "alice",
            "email": "alice@example.com",
            "password": "secret123",
        },
        db,
    )

    assert result["role"] == "USER"
    assert result["status"] == "ACTIVE"
    assert result["is_active"] is True

    db.close()


def test_staff_registration_defaults_to_pending_for_approval():
    db, _ = create_session()

    result = create_user_record(
        {
            "username": "security01",
            "email": "security@example.com",
            "password": "",
            "role": "SECURITY",
        },
        db,
        creator_role="ADMIN",
    )

    assert result["role"] == "SECURITY"
    assert result["status"] == "PENDING"
    assert result["is_active"] is False
    stored_user = db.query(User).filter(User.username == "security01").first()
    assert stored_user.password_reset_token is not None

    db.close()


def test_super_admin_creates_staff_as_active():
    db, _ = create_session()

    result = create_user_record(
        {
            "username": "operator01",
            "email": "operator@example.com",
            "password": "",
            "role": "OPERATOR",
        },
        db,
        creator_role="SUPER_ADMIN",
    )

    assert result["role"] == "OPERATOR"
    assert result["status"] == "ACTIVE"
    assert result["is_active"] is True
    stored_user = db.query(User).filter(User.username == "operator01").first()
    assert stored_user.password_reset_token is not None

    db.close()
