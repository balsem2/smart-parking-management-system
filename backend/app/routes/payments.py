from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.parking_session import ParkingSession
from app.models.payment import Payment
from app.services.monitoring import log_event
router = APIRouter(tags=["payments"])
@router.get("/payments")
def get_payments(db: Session = Depends(get_db)): return db.query(Payment).all()
@router.post("/payments")
def create_payment(payment: dict, db: Session = Depends(get_db)):
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
