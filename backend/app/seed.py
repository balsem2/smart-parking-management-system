from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import ParkingSpot, Vehicle, VehicleStatus


def seed_database():
    if not settings.seed_demo_data:
        return
    with SessionLocal() as db:
        if not db.scalar(select(func.count(ParkingSpot.id))):
            db.add_all([
                ParkingSpot(number=f"{zone}-{index:02}", zone=zone, floor=0)
                for zone in ("A", "B") for index in range(1, 11)
            ])
        if not db.scalar(select(func.count(Vehicle.id))):
            db.add_all([
                Vehicle(plate_number="123TUN4567", owner_name="Amine Ben Salah", brand="BMW", model="X3", color="Black", status=VehicleStatus.AUTHORIZED),
                Vehicle(plate_number="789TUN0123", owner_name="Sarra Mansour", brand="Peugeot", model="208", color="White", status=VehicleStatus.VIP),
                Vehicle(plate_number="111TUN9999", owner_name="Blocked Demo", status=VehicleStatus.BLACKLISTED),
            ])
        db.commit()
