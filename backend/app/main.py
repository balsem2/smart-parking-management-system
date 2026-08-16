from datetime import datetime, timezone

from core.database import Base, engine, get_db
from core.security import (
    create_access_token,
    hash_password,
    security,
    verify_access_token,
    verify_password,
)
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials
from models.alert import Alert
from models.event import Event
from models.parking_session import ParkingSession
from models.parking_spot import ParkingSpot
from models.payment import Payment
from models.reservation import Reservation
from models.user import User
from models.vehicle import Vehicle
from sqlalchemy import text
from sqlalchemy.orm import Session

Base.metadata.create_all(bind=engine)
app = FastAPI(title="SmartPark AI API", version="1.0.0")

RESERVATION_ACTIVE_STATUSES = ("PENDING", "CONFIRMED")
RESERVATION_STATUSES = (*RESERVATION_ACTIVE_STATUSES, "CANCELLED", "COMPLETED")
USER_ROLES = ("SUPER_ADMIN", "ADMIN", "OPERATOR", "SECURITY", "USER")
PAYMENT_STATUSES = ("PENDING", "PAID", "UNPAID")
ALERT_TYPES = (
    "BLACKLISTED_VEHICLE",
    "PARKING_FULL",
    "CAMERA_OFFLINE",
    "UNAUTHORIZED_ACCESS",
    "LONG_STAY",
)
LONG_STAY_THRESHOLD_MINUTES = 8 * 60

FIRST_HOUR_RATE = 2.0
ADDITIONAL_HOUR_RATE = 1.0
DAILY_MAXIMUM_RATE = 15.0


@app.get("/")
def root():
    return {"message": "Welcome to SmartPark AI API"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "SmartPark AI API"}


@app.get("/events")
def get_events(db: Session = Depends(get_db)):
    return db.query(Event).order_by(Event.created_at.desc()).all()


@app.get("/alerts")
def get_alerts(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Alert)
    if status:
        query = query.filter(Alert.status == status.upper())
    return query.order_by(Alert.created_at.desc()).all()


@app.post("/alerts")
def create_manual_alert(alert: dict, db: Session = Depends(get_db)):
    alert_type = alert.get("alert_type", "").upper()
    message = alert.get("message", "").strip()
    if alert_type not in ALERT_TYPES:
        raise HTTPException(status_code=422, detail="Invalid alert type")
    if not message:
        raise HTTPException(status_code=422, detail="Alert message is required")

    new_alert = create_alert(
        db,
        alert_type,
        message,
        severity=alert.get("severity", "WARNING").upper(),
        vehicle_id=alert.get("vehicle_id"),
        parking_session_id=alert.get("parking_session_id"),
    )
    db.commit()
    db.refresh(new_alert)
    return new_alert


@app.put("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "RESOLVED"
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert


@app.get("/db-test")
def db_test(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))

    return {"status": "success", "message": "Database connected successfully"}


@app.post("/vehicles")
def create_vehicle(vehicle: dict, db: Session = Depends(get_db)):

    new_vehicle = Vehicle(
        plate_number=vehicle["plate_number"],
        owner_name=vehicle.get("owner_name"),
        owner_phone=vehicle.get("owner_phone"),
        type=vehicle.get("type"),
        brand=vehicle.get("brand"),
        model=vehicle.get("model"),
        color=vehicle.get("color"),
        status=vehicle["status"],
    )

    db.add(new_vehicle)
    db.commit()
    db.refresh(new_vehicle)

    return {
        "message": "Vehicle created successfully",
        "id": new_vehicle.id,
        "plate_number": new_vehicle.plate_number,
    }


@app.get("/vehicles")
def get_vehicles(db: Session = Depends(get_db)):
    vehicles = db.query(Vehicle).all()

    return vehicles


@app.post("/parking-spots")
def create_parking_spot(spot: dict, db: Session = Depends(get_db)):
    new_spot = ParkingSpot(
        number=spot["number"],
        zone=spot["zone"],
        floor=spot.get("floor"),
        status=spot.get("status", "FREE"),
        vehicle_id=spot.get("vehicle_id"),
    )

    db.add(new_spot)
    db.commit()
    db.refresh(new_spot)

    return new_spot


@app.get("/parking-spots")
def get_parking_spots(db: Session = Depends(get_db)):
    spots = db.query(ParkingSpot).all()
    return spots


@app.post("/parking-sessions")
def create_parking_session(session: dict, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == session["vehicle_id"]).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if vehicle.status == "BLACKLISTED":
        log_event(
            db,
            "ACCESS_DENIED",
            "Blacklisted vehicle was denied entry",
            vehicle_id=vehicle.id,
        )
        create_alert(
            db,
            "BLACKLISTED_VEHICLE",
            "Blacklisted vehicle attempted to enter the parking",
            severity="CRITICAL",
            vehicle_id=vehicle.id,
        )
        db.commit()
        raise HTTPException(status_code=403, detail="Blacklisted vehicle cannot enter")

    parking_spot_id = session.get("parking_spot_id")
    if parking_spot_id is None:
        raise HTTPException(status_code=400, detail="Parking spot is required")

    parking_spot = (
        db.query(ParkingSpot).filter(ParkingSpot.id == parking_spot_id).first()
    )
    if not parking_spot:
        raise HTTPException(status_code=404, detail="Parking spot not found")

    if parking_spot.status != "FREE":
        raise HTTPException(status_code=400, detail="Parking spot is not available")

    active_session = (
        db.query(ParkingSession)
        .filter(
            ParkingSession.vehicle_id == vehicle.id,
            ParkingSession.status == "ACTIVE",
        )
        .first()
    )
    if active_session:
        raise HTTPException(status_code=400, detail="Vehicle already has an active session")

    new_session = ParkingSession(
        vehicle_id=vehicle.id,
        parking_spot_id=parking_spot.id,
        status="ACTIVE",
        amount=session.get("amount", 0),
    )

    db.add(new_session)
    parking_spot.status = "OCCUPIED"
    db.flush()
    log_event(
        db,
        "VEHICLE_ENTERED",
        "Vehicle entered the parking",
        vehicle_id=vehicle.id,
        parking_session_id=new_session.id,
    )
    create_parking_full_alert_if_needed(db)
    db.commit()
    db.refresh(new_session)

    return new_session


@app.get("/parking-sessions")
def get_parking_sessions(db: Session = Depends(get_db)):
    sessions = db.query(ParkingSession).all()
    return sessions


@app.post("/parking-sessions/{session_id}/exit")
def exit_parking_session(session_id: int, db: Session = Depends(get_db)):
    parking_session = (
        db.query(ParkingSession).filter(ParkingSession.id == session_id).first()
    )

    if not parking_session:
        raise HTTPException(status_code=404, detail="Parking session not found")

    if parking_session.status == "COMPLETED":
        raise HTTPException(status_code=400, detail="Parking session already completed")

    exit_time = datetime.now(timezone.utc)

    parking_session.exit_time = exit_time

    entry_time = parking_session.entry_time
    if entry_time.tzinfo is None:
        entry_time = entry_time.replace(tzinfo=timezone.utc)

    duration = exit_time - entry_time

    parking_session.duration = int(duration.total_seconds() / 60)
    parking_session.amount = calculate_parking_fee(parking_session.duration)

    parking_session.status = "COMPLETED"

    parking_spot = (
        db.query(ParkingSpot)
        .filter(ParkingSpot.id == parking_session.parking_spot_id)
        .first()
    )
    if parking_spot:
        parking_spot.status = "FREE"

    log_event(
        db,
        "VEHICLE_EXITED",
        "Vehicle exited the parking",
        vehicle_id=parking_session.vehicle_id,
        parking_session_id=parking_session.id,
    )
    if parking_session.duration >= LONG_STAY_THRESHOLD_MINUTES:
        create_alert(
            db,
            "LONG_STAY",
            "Vehicle exceeded the configured maximum parking duration",
            severity="WARNING",
            vehicle_id=parking_session.vehicle_id,
            parking_session_id=parking_session.id,
        )
    resolve_parking_full_alerts(db)

    db.commit()
    db.refresh(parking_session)

    return parking_session


@app.get("/payments")
def get_payments(db: Session = Depends(get_db)):
    return db.query(Payment).all()


@app.get("/analytics/overview")
def get_analytics_overview(db: Session = Depends(get_db)):
    parking_sessions = db.query(ParkingSession).all()
    parking_spots = db.query(ParkingSpot).all()
    paid_payments = db.query(Payment).filter(Payment.status == "PAID").all()
    completed_durations = [
        session.duration
        for session in parking_sessions
        if session.status == "COMPLETED" and session.duration is not None
    ]
    vehicle_ids_today = {
        session.vehicle_id
        for session in parking_sessions
        if is_today(session.entry_time)
    }

    return {
        "vehicles_today": len(vehicle_ids_today),
        "active_sessions": sum(
            session.status == "ACTIVE" for session in parking_sessions
        ),
        "available_spots": sum(spot.status == "FREE" for spot in parking_spots),
        "occupied_spots": sum(
            spot.status == "OCCUPIED" for spot in parking_spots
        ),
        "revenue": round(sum(payment.amount for payment in paid_payments), 2),
        "average_parking_duration_minutes": round(
            sum(completed_durations) / len(completed_durations), 2
        )
        if completed_durations
        else 0,
        "peak_hour": get_peak_hour_data(parking_sessions)["peak_hour"],
    }


@app.get("/analytics/occupancy")
def get_occupancy_analytics(db: Session = Depends(get_db)):
    parking_spots = db.query(ParkingSpot).all()
    total_spots = len(parking_spots)
    available_spots = sum(spot.status == "FREE" for spot in parking_spots)
    occupied_spots = sum(spot.status == "OCCUPIED" for spot in parking_spots)

    return {
        "total_spots": total_spots,
        "available_spots": available_spots,
        "occupied_spots": occupied_spots,
        "occupancy_rate_percent": round(occupied_spots / total_spots * 100, 2)
        if total_spots
        else 0,
    }


@app.get("/analytics/revenue")
def get_revenue_analytics(db: Session = Depends(get_db)):
    payments = db.query(Payment).all()
    paid_payments = [payment for payment in payments if payment.status == "PAID"]

    return {
        "total_revenue": round(sum(payment.amount for payment in paid_payments), 2),
        "paid_payments": len(paid_payments),
        "pending_payments": sum(
            payment.status == "PENDING" for payment in payments
        ),
        "unpaid_payments": sum(payment.status == "UNPAID" for payment in payments),
    }


@app.get("/analytics/vehicles")
def get_vehicle_analytics(db: Session = Depends(get_db)):
    today_sessions = [
        session for session in db.query(ParkingSession).all() if is_today(session.entry_time)
    ]

    return {
        "vehicles_today": len({session.vehicle_id for session in today_sessions}),
        "entries_today": len(today_sessions),
        "active_vehicles": len(
            {session.vehicle_id for session in today_sessions if session.status == "ACTIVE"}
        ),
    }


@app.get("/analytics/peak-hours")
def get_peak_hours_analytics(db: Session = Depends(get_db)):
    return get_peak_hour_data(db.query(ParkingSession).all())


@app.post("/payments")
def create_payment(payment: dict, db: Session = Depends(get_db)):
    parking_session_id = payment.get("parking_session_id")
    if not isinstance(parking_session_id, int):
        raise HTTPException(status_code=422, detail="parking_session_id must be an integer")

    parking_session = (
        db.query(ParkingSession)
        .filter(ParkingSession.id == parking_session_id)
        .first()
    )
    if not parking_session:
        raise HTTPException(status_code=404, detail="Parking session not found")
    if parking_session.status != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail="Payment can only be created for a completed parking session",
        )
    if db.query(Payment).filter(Payment.parking_session_id == parking_session.id).first():
        raise HTTPException(status_code=409, detail="Payment already exists for this session")

    payment_status = payment.get("status", "PENDING").upper()
    if payment_status not in PAYMENT_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid payment status")

    new_payment = Payment(
        parking_session_id=parking_session.id,
        amount=parking_session.amount,
        status=payment_status,
        payment_method=payment.get("payment_method"),
        paid_at=datetime.now(timezone.utc) if payment_status == "PAID" else None,
    )
    db.add(new_payment)
    db.flush()
    if payment_status == "PAID":
        log_event(
            db,
            "PAYMENT_COMPLETED",
            "Parking payment completed",
            parking_session_id=parking_session.id,
            payment_id=new_payment.id,
        )
    db.commit()
    db.refresh(new_payment)

    return new_payment


def calculate_parking_fee(duration_minutes: int) -> float:
    """Calculate the fee for each started 24-hour period."""
    if duration_minutes <= 0:
        return FIRST_HOUR_RATE

    full_days, remaining_minutes = divmod(duration_minutes, 24 * 60)
    total = full_days * DAILY_MAXIMUM_RATE

    if remaining_minutes == 0:
        return total
    if remaining_minutes <= 60:
        return total + FIRST_HOUR_RATE

    additional_hours = (remaining_minutes - 60 + 59) // 60
    return total + min(
        FIRST_HOUR_RATE + additional_hours * ADDITIONAL_HOUR_RATE,
        DAILY_MAXIMUM_RATE,
    )


def is_today(value: datetime | None) -> bool:
    if value is None:
        return False
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.date() == datetime.now(timezone.utc).date()


def get_peak_hour_data(parking_sessions: list[ParkingSession]) -> dict:
    hourly_entries = [0] * 24
    for parking_session in parking_sessions:
        entry_time = parking_session.entry_time
        if entry_time is None:
            continue
        if entry_time.tzinfo is None:
            entry_time = entry_time.replace(tzinfo=timezone.utc)
        hourly_entries[entry_time.hour] += 1

    peak_entries = max(hourly_entries)
    peak_hour = hourly_entries.index(peak_entries) if peak_entries else None

    return {
        "peak_hour": f"{peak_hour:02d}:00" if peak_hour is not None else None,
        "peak_entries": peak_entries,
        "hourly_entries": [
            {"hour": f"{hour:02d}:00", "entries": entries}
            for hour, entries in enumerate(hourly_entries)
            if entries
        ],
    }


@app.put("/parking-spots/{spot_id}/status")
def update_spot_status(spot_id: int, data: dict, db: Session = Depends(get_db)):
    spot = db.query(ParkingSpot).filter(ParkingSpot.id == spot_id).first()

    if not spot:
        return {"error": "Parking spot not found"}

    spot.status = data["status"]

    db.commit()
    db.refresh(spot)

    return {
        "message": "Parking spot status updated successfully",
        "id": spot.id,
        "number": spot.number,
        "status": spot.status,
    }


@app.post("/reservations")
def create_reservation(reservation: dict, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == reservation["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    vehicle = db.query(Vehicle).filter(Vehicle.id == reservation["vehicle_id"]).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    parking_spot = (
        db.query(ParkingSpot)
        .filter(ParkingSpot.id == reservation["parking_spot_id"])
        .first()
    )
    if not parking_spot:
        raise HTTPException(status_code=404, detail="Parking spot not found")

    start_time = parse_reservation_datetime(reservation["start_time"], "start_time")
    end_time = parse_reservation_datetime(reservation["end_time"], "end_time")
    validate_reservation_period(start_time, end_time)
    ensure_spot_is_available(
        db, parking_spot.id, start_time, end_time
    )

    new_reservation = Reservation(
        user_id=user.id,
        vehicle_id=vehicle.id,
        parking_spot_id=parking_spot.id,
        start_time=start_time,
        end_time=end_time,
        status="PENDING",
    )

    db.add(new_reservation)
    db.flush()
    log_event(
        db,
        "RESERVATION_CREATED",
        "Parking reservation created",
        vehicle_id=vehicle.id,
        reservation_id=new_reservation.id,
        user_id=user.id,
    )
    db.commit()
    db.refresh(new_reservation)

    return new_reservation


@app.get("/reservations")
def get_reservations(db: Session = Depends(get_db)):
    reservations = db.query(Reservation).all()
    return reservations


@app.get("/reservations/{reservation_id}")
def get_reservation(reservation_id: int, db: Session = Depends(get_db)):
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()

    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    return reservation


@app.put("/reservations/{reservation_id}")
def update_reservation(
    reservation_id: int, data: dict, db: Session = Depends(get_db)
):
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()

    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    if reservation.status in ("CANCELLED", "COMPLETED"):
        raise HTTPException(status_code=400, detail="This reservation cannot be updated")

    user_id = data.get("user_id", reservation.user_id)
    vehicle_id = data.get("vehicle_id", reservation.vehicle_id)
    parking_spot_id = data.get("parking_spot_id", reservation.parking_spot_id)
    start_time = parse_reservation_datetime(
        data.get("start_time", reservation.start_time), "start_time"
    )
    end_time = parse_reservation_datetime(
        data.get("end_time", reservation.end_time), "end_time"
    )
    status_value = data.get("status", reservation.status).upper()

    if status_value not in RESERVATION_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid reservation status")

    if not db.query(User).filter(User.id == user_id).first():
        raise HTTPException(status_code=404, detail="User not found")
    if not db.query(Vehicle).filter(Vehicle.id == vehicle_id).first():
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if not db.query(ParkingSpot).filter(ParkingSpot.id == parking_spot_id).first():
        raise HTTPException(status_code=404, detail="Parking spot not found")

    validate_reservation_period(start_time, end_time)
    if status_value in RESERVATION_ACTIVE_STATUSES:
        ensure_spot_is_available(
            db, parking_spot_id, start_time, end_time, excluded_reservation_id=reservation.id
        )

    reservation.user_id = user_id
    reservation.vehicle_id = vehicle_id
    reservation.parking_spot_id = parking_spot_id
    reservation.start_time = start_time
    reservation.end_time = end_time
    reservation.status = status_value

    db.commit()
    db.refresh(reservation)

    return reservation


@app.delete("/reservations/{reservation_id}")
def delete_reservation(reservation_id: int, db: Session = Depends(get_db)):
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()

    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    db.delete(reservation)
    db.commit()

    return {"message": "Reservation deleted successfully"}


def parse_reservation_datetime(value: str | datetime, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed_value = value
    elif isinstance(value, str):
        try:
            parsed_value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"{field_name} must use ISO 8601 datetime format",
            ) from exc
    else:
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} must use ISO 8601 datetime format",
        )

    if parsed_value.tzinfo is None:
        return parsed_value.replace(tzinfo=timezone.utc)

    return parsed_value


def validate_reservation_period(start_time: datetime, end_time: datetime) -> None:
    if start_time >= end_time:
        raise HTTPException(status_code=422, detail="end_time must be after start_time")


def ensure_spot_is_available(
    db: Session,
    parking_spot_id: int,
    start_time: datetime,
    end_time: datetime,
    excluded_reservation_id: int | None = None,
) -> None:
    query = db.query(Reservation).filter(
        Reservation.parking_spot_id == parking_spot_id,
        Reservation.status.in_(RESERVATION_ACTIVE_STATUSES),
        Reservation.start_time < end_time,
        Reservation.end_time > start_time,
    )

    if excluded_reservation_id is not None:
        query = query.filter(Reservation.id != excluded_reservation_id)

    if query.first():
        raise HTTPException(
            status_code=409,
            detail="Parking spot is already reserved during this period",
        )


@app.post("/users")
def create_user(user: dict, db: Session = Depends(get_db)):
    username = user.get("username", "").strip()
    email = user.get("email", "").strip().lower()
    password = user.get("password", "")
    role = user.get("role", "USER").upper()

    validate_user_details(username, email, password, role)
    ensure_user_is_unique(db, username, email)

    new_user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=user.get("is_active", True),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User created successfully",
        "id": new_user.id,
        "username": new_user.username,
        "email": new_user.email,
        "role": new_user.role,
        "is_active": new_user.is_active,
    }


@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()

    return users


@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@app.put("/users/{user_id}")
def update_user(user_id: int, data: dict, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    username = data.get("username", user.username).strip()
    email = data.get("email", user.email).strip().lower()
    role = data.get("role", user.role).upper()
    password = data.get("password")

    validate_user_details(username, email, password, role, password_is_optional=True)
    ensure_user_is_unique(db, username, email, excluded_user_id=user.id)

    user.username = username
    user.email = email
    user.role = role

    if password:
        user.password_hash = hash_password(password)
    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            raise HTTPException(status_code=422, detail="is_active must be a boolean")
        user.is_active = data["is_active"]

    db.commit()
    db.refresh(user)

    return user


@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    has_reservations = db.query(Reservation).filter(Reservation.user_id == user.id).first()
    if has_reservations:
        raise HTTPException(
            status_code=409,
            detail="User has reservations and cannot be deleted; deactivate the user instead",
        )

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}


@app.post("/register")
def register(user: dict, db: Session = Depends(get_db)):
    user["role"] = "USER"
    return create_user(user, db)


@app.post("/auth/login")
@app.post("/login")
def login(credentials: dict, db: Session = Depends(get_db)):
    username = credentials.get("username", "").strip()
    password = credentials.get("password", "")
    user = db.query(User).filter(User.username == username).first()

    if not user or not user.is_active or not verify_password(password, user.password_hash):
        log_event(db, "ACCESS_DENIED", "Invalid login attempt", user_id=user.id if user else None)
        create_alert(
            db,
            "UNAUTHORIZED_ACCESS",
            "Invalid login attempt detected",
            severity="WARNING",
            vehicle_id=None,
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(
        {"user_id": user.id, "username": user.username, "role": user.role}
    )

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
    }


def validate_user_details(
    username: str,
    email: str,
    password: str | None,
    role: str,
    password_is_optional: bool = False,
) -> None:
    if not username or len(username) < 3:
        raise HTTPException(status_code=422, detail="username must contain at least 3 characters")
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(status_code=422, detail="email must be valid")
    if not password_is_optional or password:
        if not password or len(password) < 8:
            raise HTTPException(status_code=422, detail="password must contain at least 8 characters")
    if role not in USER_ROLES:
        raise HTTPException(status_code=422, detail="Invalid user role")


def ensure_user_is_unique(
    db: Session,
    username: str,
    email: str,
    excluded_user_id: int | None = None,
) -> None:
    query = db.query(User).filter((User.username == username) | (User.email == email))

    if excluded_user_id is not None:
        query = query.filter(User.id != excluded_user_id)

    if query.first():
        raise HTTPException(status_code=409, detail="Username or email is already in use")


def log_event(
    db: Session,
    event_type: str,
    description: str,
    *,
    vehicle_id: int | None = None,
    parking_session_id: int | None = None,
    reservation_id: int | None = None,
    payment_id: int | None = None,
    user_id: int | None = None,
) -> Event:
    event = Event(
        event_type=event_type,
        description=description,
        vehicle_id=vehicle_id,
        parking_session_id=parking_session_id,
        reservation_id=reservation_id,
        payment_id=payment_id,
        user_id=user_id,
    )
    db.add(event)
    return event


def create_alert(
    db: Session,
    alert_type: str,
    message: str,
    *,
    severity: str = "WARNING",
    vehicle_id: int | None = None,
    parking_session_id: int | None = None,
) -> Alert:
    alert = Alert(
        alert_type=alert_type,
        message=message,
        severity=severity,
        vehicle_id=vehicle_id,
        parking_session_id=parking_session_id,
    )
    db.add(alert)
    return alert


def create_parking_full_alert_if_needed(db: Session) -> None:
    free_spots = db.query(ParkingSpot).filter(ParkingSpot.status == "FREE").count()
    active_alert = (
        db.query(Alert)
        .filter(Alert.alert_type == "PARKING_FULL", Alert.status == "ACTIVE")
        .first()
    )
    if free_spots == 0 and not active_alert:
        create_alert(
            db,
            "PARKING_FULL",
            "No parking spots are currently available",
            severity="WARNING",
        )


def resolve_parking_full_alerts(db: Session) -> None:
    active_alerts = (
        db.query(Alert)
        .filter(Alert.alert_type == "PARKING_FULL", Alert.status == "ACTIVE")
        .all()
    )
    for alert in active_alerts:
        alert.status = "RESOLVED"
        alert.resolved_at = datetime.now(timezone.utc)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
):
    payload = verify_access_token(credentials)

    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive")

    return user


@app.get("/me")
def get_my_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
    }
