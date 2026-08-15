from fastapi import FastAPI, Depends, Security, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from core.database import get_db
from core.database import engine, Base
from models.vehicle import Vehicle
from models.parking_spot import ParkingSpot
from models.parking_session import ParkingSession
from models.reservation import Reservation
from models.user import User
from datetime import datetime, timezone
from core.database import engine, Base
from core.security import hash_password, verify_password, create_access_token
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import Security
from core.security import security, verify_access_token
Base.metadata.create_all(bind=engine)
app = FastAPI(
    title="SmartPark AI API",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "message": "Welcome to SmartPark AI API"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "SmartPark AI API"
    }
@app.get("/db-test")
def db_test(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))

    return {
        "status": "success",
        "message": "Database connected successfully"
    }
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
        status=vehicle["status"]
    )

    db.add(new_vehicle)
    db.commit()
    db.refresh(new_vehicle)

    return {
        "message": "Vehicle created successfully",
        "id": new_vehicle.id,
        "plate_number": new_vehicle.plate_number
    }
@app.get("/vehicles")
def get_vehicles(db: Session = Depends(get_db)):
    vehicles = db.query(Vehicle).all()

    return vehicles
@app.post("/parking-spots")
def create_parking_spot(
    spot: dict,
    db: Session = Depends(get_db)
):
    new_spot = ParkingSpot(
        number=spot["number"],
        zone=spot["zone"],
        floor=spot.get("floor"),
        status=spot.get("status", "FREE"),
        vehicle_id=spot.get("vehicle_id")
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
def create_parking_session(
    session: dict,
    db: Session = Depends(get_db)
):
    new_session = ParkingSession(
        vehicle_id=session["vehicle_id"],
        parking_spot_id=session.get("parking_spot_id"),
        status=session.get("status", "ACTIVE"),
        amount=session.get("amount", 0)
    )

    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return new_session


@app.get("/parking-sessions")
def get_parking_sessions(db: Session = Depends(get_db)):
    sessions = db.query(ParkingSession).all()
    return sessions 


@app.post("/parking-sessions/{session_id}/exit")
def exit_parking_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    parking_session = (
        db.query(ParkingSession)
        .filter(ParkingSession.id == session_id)
        .first()
    )

    if not parking_session:
        raise HTTPException(
            status_code=404,
            detail="Parking session not found"
        )

    if parking_session.status == "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail="Parking session already completed"
        )

    exit_time = datetime.now(timezone.utc)

    parking_session.exit_time = exit_time

    duration = exit_time - parking_session.entry_time

    parking_session.duration = int(
        duration.total_seconds() / 60
    )

    parking_session.status = "COMPLETED"

    db.commit()
    db.refresh(parking_session)

    return parking_session

@app.put("/parking-spots/{spot_id}/status")
def update_spot_status(
    spot_id: int,
    data: dict,
    db: Session = Depends(get_db)
):
    spot = db.query(ParkingSpot).filter(
        ParkingSpot.id == spot_id
    ).first()

    if not spot:
        return {
            "error": "Parking spot not found"
        }

    spot.status = data["status"]

    db.commit()
    db.refresh(spot)

    return {
        "message": "Parking spot status updated successfully",
        "id": spot.id,
        "number": spot.number,
        "status": spot.status
    }
@app.post("/reservations")
def create_reservation(
    reservation: dict,
    db: Session = Depends(get_db)
):
    existing_reservation = db.query(Reservation).filter(
        Reservation.parking_spot_id == reservation["parking_spot_id"],
        Reservation.status != "CANCELLED",
        Reservation.start_time < reservation["end_time"],
        Reservation.end_time > reservation["start_time"]
    ).first()

    if existing_reservation:
        return {
            "message": "Parking spot is already reserved during this period"
        }

    new_reservation = Reservation(
        vehicle_id=reservation["vehicle_id"],
        parking_spot_id=reservation["parking_spot_id"],
        start_time=reservation["start_time"],
        end_time=reservation["end_time"],
        status=reservation.get("status", "PENDING")
    )

    db.add(new_reservation)
    db.commit()
    db.refresh(new_reservation)

    return new_reservation

@app.get("/reservations")
def get_reservations(db: Session = Depends(get_db)):
    reservations = db.query(Reservation).all()
    return reservations
@app.put("/reservations/{reservation_id}/status")
def update_reservation_status(
    reservation_id: int,
    data: dict,
    db: Session = Depends(get_db)
):
    reservation = db.query(Reservation).filter(
        Reservation.id == reservation_id
    ).first()

    if not reservation:
        return {
            "message": "Reservation not found"
        }

    reservation.status = data["status"]

    db.commit()
    db.refresh(reservation)

    return {
        "message": "Reservation status updated successfully",
        "id": reservation.id,
        "status": reservation.status
    }
@app.post("/users")
def create_user(
    user: dict,
    db: Session = Depends(get_db)
):
    new_user = User(
        username=user["username"],
        email=user["email"],
        password_hash=hash_password(user["password"]),
        role=user.get("role", "USER"),
        is_active=user.get("is_active", True)
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
        "is_active": new_user.is_active
    }

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()

    return users

@app.post("/auth/login")
def login(
    credentials: dict,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.username == credentials["username"]
    ).first()

    if not user:
        return {
            "message": "Invalid username or password"
        }

    if not user.is_active:
        return {
            "message": "User account is inactive"
        }

    if not verify_password(
        credentials["password"],
        user.password_hash
    ):
        return {
            "message": "Invalid username or password"
        }

    access_token = create_access_token({
        "user_id": user.id,
        "username": user.username,
        "role": user.role
    })

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer"
    }
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
):
    payload = verify_access_token(credentials)

    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="User is inactive"
        )

    return user
@app.get("/me")
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active
    }