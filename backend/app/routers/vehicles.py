from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Vehicle, VehicleStatus
from app.schemas import VehicleCreate, VehicleRead, VehicleUpdate

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleRead])
def list_vehicles(status_filter: VehicleStatus | None = Query(None, alias="status"), db: Session = Depends(get_db)):
    query = select(Vehicle).order_by(Vehicle.created_at.desc())
    if status_filter:
        query = query.where(Vehicle.status == status_filter)
    return db.scalars(query).all()


@router.post("", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
def create_vehicle(payload: VehicleCreate, db: Session = Depends(get_db)):
    vehicle = Vehicle(**payload.model_dump())
    db.add(vehicle)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Plate number already exists")
    db.refresh(vehicle)
    return vehicle


@router.get("/{vehicle_id}", response_model=VehicleRead)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(404, "Vehicle not found")
    return vehicle


@router.patch("/{vehicle_id}", response_model=VehicleRead)
def update_vehicle(vehicle_id: int, payload: VehicleUpdate, db: Session = Depends(get_db)):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(404, "Vehicle not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(vehicle, key, value)
    db.commit()
    db.refresh(vehicle)
    return vehicle
