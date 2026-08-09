from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ParkingSpot, Reservation, ReservationStatus, SpotStatus, Vehicle
from app.schemas import ReservationCreate, ReservationRead

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.get("", response_model=list[ReservationRead])
def list_reservations(db: Session = Depends(get_db)):
    return db.scalars(select(Reservation).order_by(Reservation.start_time.desc())).all()


@router.post("", response_model=ReservationRead, status_code=status.HTTP_201_CREATED)
def create_reservation(payload: ReservationCreate, db: Session = Depends(get_db)):
    if payload.end_time <= payload.start_time:
        raise HTTPException(422, "end_time must be after start_time")
    if not db.get(Vehicle, payload.vehicle_id):
        raise HTTPException(404, "Vehicle not found")
    conflicts = select(Reservation.spot_id).where(
        Reservation.status.in_([ReservationStatus.CONFIRMED, ReservationStatus.ACTIVE]),
        and_(Reservation.start_time < payload.end_time, Reservation.end_time > payload.start_time),
    )
    spot_query = select(ParkingSpot).where(
        ParkingSpot.status != SpotStatus.OUT_OF_SERVICE,
        ~ParkingSpot.id.in_(conflicts),
    )
    if payload.zone:
        spot_query = spot_query.where(ParkingSpot.zone == payload.zone)
    spot = db.scalar(spot_query.order_by(ParkingSpot.number).limit(1))
    if not spot:
        raise HTTPException(409, "No spot available for this period")
    reservation = Reservation(spot_id=spot.id, **payload.model_dump(exclude={"zone"}))
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation


@router.post("/{reservation_id}/cancel", response_model=ReservationRead)
def cancel_reservation(reservation_id: int, db: Session = Depends(get_db)):
    reservation = db.get(Reservation, reservation_id)
    if not reservation:
        raise HTTPException(404, "Reservation not found")
    if reservation.status not in (ReservationStatus.CONFIRMED, ReservationStatus.ACTIVE):
        raise HTTPException(409, "Reservation cannot be cancelled")
    reservation.status = ReservationStatus.CANCELLED
    db.commit()
    db.refresh(reservation)
    return reservation
