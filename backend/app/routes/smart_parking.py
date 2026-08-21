from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.authorization import require_roles
from app.core.database import get_db
from app.models.parking_session import ParkingSession
from app.models.parking_spot import ParkingSpot
from app.models.payment import Payment
from app.models.reservation import Reservation
from app.models.vehicle import Vehicle
from app.services.billing import calculate_parking_fee

router = APIRouter(tags=["smart-parking"])

# Coordinates are used only to open a navigation route. Configure real parking
# addresses/coordinates here when deploying each facility.
ZONE_DETAILS = {
    "A": {"name": "SmartPark Centre", "address": "Avenue Habib Bourguiba, Tunis", "latitude": 36.8065, "longitude": 10.1815},
    "B": {"name": "SmartPark Lafayette", "address": "Rue du Lac, Tunis", "latitude": 36.8185, "longitude": 10.1819},
    "C": {"name": "SmartPark Berges du Lac", "address": "Les Berges du Lac, Tunis", "latitude": 36.8360, "longitude": 10.2350},
}


def zone_options(db: Session):
    spots = db.query(ParkingSpot).all()
    sessions = db.query(ParkingSession).all()
    current_hour = datetime.now(timezone.utc).hour
    result = []
    for zone in sorted({spot.zone for spot in spots}):
        zone_spots = [spot for spot in spots if spot.zone == zone]
        total = len(zone_spots)
        free = sum(spot.status == "FREE" for spot in zone_spots)
        occupied = sum(spot.status == "OCCUPIED" for spot in zone_spots)
        historical = [session for session in sessions if session.parking_spot and session.parking_spot.zone == zone and session.entry_time and (session.entry_time.replace(tzinfo=timezone.utc) if session.entry_time.tzinfo is None else session.entry_time).hour == current_hour]
        historical_pressure = min(1, len(historical) / max(total, 1))
        live_probability = int(round(max(5, min(98, (free / max(total, 1)) * 100 * 0.7 + (1 - historical_pressure) * 30))))
        details = ZONE_DETAILS.get(zone, {"name": f"SmartPark Zone {zone}", "address": f"Zone {zone}, Tunis", "latitude": 36.81, "longitude": 10.18})
        result.append({
            "zone": zone, **details, "total_spots": total, "available_spots": free,
            "occupied_spots": occupied, "occupancy_percent": round((occupied / total) * 100) if total else 0,
            "price_1h": calculate_parking_fee(60), "price_2h": calculate_parking_fee(120),
            "day_price": calculate_parking_fee(1440), "monthly_pass_price": 45.0,
            "availability_probability": live_probability,
            "recommendation_score": round((free / max(total, 1)) * 70 + (1 - historical_pressure) * 30),
        })
    return sorted(result, key=lambda item: (-item["recommendation_score"], item["price_1h"]))


@router.get("/smart-parking/options")
def smart_parking_options(db: Session = Depends(get_db), current_user=Depends(require_roles("USER", "SUPER_ADMIN", "ADMIN", "OPERATOR", "SECURITY"))):
    return {"generated_at": datetime.now(timezone.utc), "options": zone_options(db)}


@router.get("/smart-parking/my-ticket")
def my_digital_ticket(db: Session = Depends(get_db), current_user=Depends(require_roles("USER"))):
    vehicle_ids = db.query(Vehicle.id).filter(Vehicle.user_id == current_user.id)
    session = db.query(ParkingSession).filter(ParkingSession.vehicle_id.in_(vehicle_ids), ParkingSession.status == "ACTIVE").order_by(ParkingSession.entry_time.desc()).first()
    reservation = db.query(Reservation).filter(Reservation.user_id == current_user.id, Reservation.status == "CONFIRMED").order_by(Reservation.start_time.asc()).first()
    if session:
        return {"type": "SESSION", "id": session.id, "spot": session.parking_spot.number, "zone": session.parking_spot.zone, "issued_at": session.entry_time, "qr_value": f"SMARTPARK:SESSION:{session.id}:{session.vehicle_id}"}
    if reservation:
        return {"type": "RESERVATION", "id": reservation.id, "spot": reservation.parking_spot.number, "zone": reservation.parking_spot.zone, "issued_at": reservation.start_time, "qr_value": f"SMARTPARK:RESERVATION:{reservation.id}:{reservation.vehicle_id}"}
    return {"type": None, "message": "No active ticket found"}


@router.get("/smart-parking/find-my-car")
def find_my_car(db: Session = Depends(get_db), current_user=Depends(require_roles("USER"))):
    vehicle_ids = db.query(Vehicle.id).filter(Vehicle.user_id == current_user.id)
    session = db.query(ParkingSession).filter(ParkingSession.vehicle_id.in_(vehicle_ids)).order_by(ParkingSession.entry_time.desc()).first()
    if not session:
        return {"found": False, "message": "No parking history found for your vehicles"}
    spot = session.parking_spot
    details = ZONE_DETAILS.get(spot.zone, {})
    return {"found": True, "spot": spot.number, "zone": spot.zone, "floor": spot.floor, "parking_name": details.get("name", f"SmartPark Zone {spot.zone}"), "address": details.get("address", "Tunis"), "latitude": details.get("latitude"), "longitude": details.get("longitude"), "active": session.status == "ACTIVE"}


@router.get("/smart-parking/rewards")
def rewards(db: Session = Depends(get_db), current_user=Depends(require_roles("USER"))):
    vehicle_ids = {vehicle_id for (vehicle_id,) in db.query(Vehicle.id).filter(Vehicle.user_id == current_user.id).all()}
    payments = db.query(Payment).outerjoin(ParkingSession).outerjoin(Reservation).filter(Payment.status == "PAID").all()
    mine = [payment for payment in payments if (payment.parking_session and payment.parking_session.vehicle_id in vehicle_ids) or (payment.reservation and payment.reservation.user_id == current_user.id)]
    points = int(sum(payment.amount for payment in mine) * 10)
    return {"points": points, "next_reward_at": ((points // 100) + 1) * 100, "discount_value": round((points // 100) * 1.0, 2), "visits": len(mine)}


@router.get("/smart-parking/owner-dashboard")
def owner_dashboard(db: Session = Depends(get_db), current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR"))):
    options = zone_options(db)
    payments = db.query(Payment).filter(Payment.status == "PAID").all()
    sessions = db.query(ParkingSession).all()
    return {"zones": options, "revenue": round(sum(payment.amount for payment in payments), 2), "active_sessions": sum(session.status == "ACTIVE" for session in sessions), "completed_sessions": sum(session.status == "COMPLETED" for session in sessions), "peak_hour": max(range(24), key=lambda hour: sum(1 for session in sessions if session.entry_time and (session.entry_time.replace(tzinfo=timezone.utc) if session.entry_time.tzinfo is None else session.entry_time).hour == hour))}
