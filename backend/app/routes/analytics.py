from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.parking_session import ParkingSession
from app.models.parking_spot import ParkingSpot
from app.models.payment import Payment
router = APIRouter(tags=["analytics"])
def today(value):
    if not value: return False
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value).date() == datetime.now(timezone.utc).date()
def peak(sessions):
    hours = [0]*24
    for s in sessions:
        if s.entry_time: hours[(s.entry_time.replace(tzinfo=timezone.utc) if s.entry_time.tzinfo is None else s.entry_time).hour] += 1
    n=max(hours); h=hours.index(n) if n else None
    return {"peak_hour": f"{h:02d}:00" if h is not None else None, "peak_entries": n, "hourly_entries":[{"hour":f"{i:02d}:00","entries":v} for i,v in enumerate(hours) if v]}
@router.get("/analytics/overview")
def overview(db: Session = Depends(get_db)):
    sessions, spots, paid = db.query(ParkingSession).all(), db.query(ParkingSpot).all(), db.query(Payment).filter(Payment.status=="PAID").all(); durations=[s.duration for s in sessions if s.status=="COMPLETED" and s.duration is not None]
    return {"vehicles_today":len({s.vehicle_id for s in sessions if today(s.entry_time)}),"active_sessions":sum(s.status=="ACTIVE" for s in sessions),"available_spots":sum(s.status=="FREE" for s in spots),"occupied_spots":sum(s.status=="OCCUPIED" for s in spots),"revenue":round(sum(p.amount for p in paid),2),"average_parking_duration_minutes":round(sum(durations)/len(durations),2) if durations else 0,"peak_hour":peak(sessions)["peak_hour"]}
@router.get("/analytics/occupancy")
def occupancy(db: Session = Depends(get_db)):
    spots=db.query(ParkingSpot).all(); total=len(spots); occupied=sum(s.status=="OCCUPIED" for s in spots); available=sum(s.status=="FREE" for s in spots); return {"total_spots":total,"available_spots":available,"occupied_spots":occupied,"occupancy_rate_percent":round(occupied/total*100,2) if total else 0}
@router.get("/analytics/revenue")
def revenue(db: Session = Depends(get_db)):
    payments=db.query(Payment).all(); paid=[p for p in payments if p.status=="PAID"]; return {"total_revenue":round(sum(p.amount for p in paid),2),"paid_payments":len(paid),"pending_payments":sum(p.status=="PENDING" for p in payments),"unpaid_payments":sum(p.status=="UNPAID" for p in payments)}
@router.get("/analytics/vehicles")
def vehicles(db: Session = Depends(get_db)):
    sessions=[s for s in db.query(ParkingSession).all() if today(s.entry_time)]; return {"vehicles_today":len({s.vehicle_id for s in sessions}),"entries_today":len(sessions),"active_vehicles":len({s.vehicle_id for s in sessions if s.status=="ACTIVE"})}
@router.get("/analytics/peak-hours")
def peak_hours(db: Session = Depends(get_db)): return peak(db.query(ParkingSession).all())
