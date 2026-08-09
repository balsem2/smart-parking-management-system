from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ParkingSession, ParkingSpot, SessionStatus, SpotStatus
from app.schemas import SessionRead, SpotCreate, SpotRead

router = APIRouter(prefix="/parking", tags=["parking"])


@router.get("/spots", response_model=list[SpotRead])
def list_spots(db: Session = Depends(get_db)):
    return db.scalars(select(ParkingSpot).order_by(ParkingSpot.zone, ParkingSpot.number)).all()


@router.post("/spots", response_model=SpotRead, status_code=status.HTTP_201_CREATED)
def create_spot(payload: SpotCreate, db: Session = Depends(get_db)):
    spot = ParkingSpot(**payload.model_dump())
    db.add(spot)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Spot number already exists")
    db.refresh(spot)
    return spot


@router.get("/sessions", response_model=list[SessionRead])
def list_sessions(active_only: bool = False, db: Session = Depends(get_db)):
    query = select(ParkingSession).order_by(ParkingSession.entry_time.desc())
    if active_only:
        query = query.where(ParkingSession.status == SessionStatus.ACTIVE)
    return db.scalars(query).all()


@router.get("/summary")
def parking_summary(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(ParkingSpot.id))) or 0
    occupied = db.scalar(select(func.count(ParkingSpot.id)).where(ParkingSpot.status == SpotStatus.OCCUPIED)) or 0
    reserved = db.scalar(select(func.count(ParkingSpot.id)).where(ParkingSpot.status == SpotStatus.RESERVED)) or 0
    available = db.scalar(select(func.count(ParkingSpot.id)).where(ParkingSpot.status == SpotStatus.FREE)) or 0
    return {
        "capacity": total,
        "occupied": occupied,
        "reserved": reserved,
        "available": available,
        "occupancy_rate": round(occupied / total * 100, 1) if total else 0,
    }
