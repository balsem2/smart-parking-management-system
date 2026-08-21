from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.authorization import require_roles
from app.models.parking_session import ParkingSession
from app.models.payment import Payment
from app.models.reservation import Reservation
from app.models.vehicle import Vehicle
from app.services.monitoring import log_event
router = APIRouter(tags=["payments"])
@router.get("/payments")
def get_payments(db: Session = Depends(get_db), current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR", "USER"))):
    query = db.query(Payment)
    if current_user.role == "USER":
        vehicle_ids = db.query(Vehicle.id).filter(Vehicle.user_id == current_user.id)
        query = query.outerjoin(ParkingSession).outerjoin(Reservation).filter(
            or_(ParkingSession.vehicle_id.in_(vehicle_ids), Reservation.user_id == current_user.id)
        )
    return query.all()
@router.post("/payments")
def create_payment(payment: dict, db: Session = Depends(get_db), current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR"))):
    session_id = payment.get("parking_session_id")
    if not isinstance(session_id, int): raise HTTPException(status_code=422, detail="parking_session_id must be an integer")
    session = db.query(ParkingSession).filter(ParkingSession.id == session_id).first()
    if not session: raise HTTPException(status_code=404, detail="Parking session not found")
    if session.status != "COMPLETED": raise HTTPException(status_code=400, detail="Payment can only be created for a completed parking session")
    if db.query(Payment).filter(Payment.parking_session_id == session.id).first(): raise HTTPException(status_code=409, detail="Payment already exists for this session")
    status = payment.get("status", "PENDING").upper()
    if status not in {"PENDING", "PAID", "UNPAID"}: raise HTTPException(status_code=422, detail="Invalid payment status")
    result = Payment(parking_session_id=session.id, amount=session.amount, status=status, payment_method=payment.get("payment_method"), paid_at=datetime.now(timezone.utc) if status == "PAID" else None); db.add(result); db.flush()
    if status == "PAID": log_event(db, "PAYMENT_COMPLETED", "Parking payment completed", parking_session_id=session.id, payment_id=result.id)
    db.commit(); db.refresh(result); return result

@router.put("/payments/{payment_id}/pay")
def pay_payment(payment_id: int, data: dict, db: Session = Depends(get_db), current_user=Depends(require_roles("USER"))):
    result = db.query(Payment).filter(Payment.id == payment_id).first()
    if not result: raise HTTPException(status_code=404, detail="Payment not found")
    session = db.query(ParkingSession).filter(ParkingSession.id == result.parking_session_id).first()
    reservation = db.query(Reservation).filter(Reservation.id == result.reservation_id).first() if result.reservation_id else None
    vehicle = db.query(Vehicle).filter(Vehicle.id == session.vehicle_id).first() if session else None
    owns_session = vehicle and vehicle.user_id == current_user.id
    owns_reservation = reservation and reservation.user_id == current_user.id
    if not owns_session and not owns_reservation: raise HTTPException(status_code=403, detail="You can only pay for your own parking")
    if result.status == "PAID": raise HTTPException(status_code=400, detail="Payment is already completed")
    result.status, result.payment_method, result.paid_at = "PAID", str(data.get("payment_method", "CARD")).strip().upper(), datetime.now(timezone.utc)
    if reservation:
        reservation.status = "CONFIRMED"
    log_event(db, "PAYMENT_COMPLETED", "Parking payment completed", parking_session_id=session.id if session else None, reservation_id=reservation.id if reservation else None, payment_id=result.id, user_id=current_user.id)
    db.commit(); db.refresh(result); return result
