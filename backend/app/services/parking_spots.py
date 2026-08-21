from sqlalchemy.orm import Session

from app.models.parking_spot import ParkingSpot


VALID_SPOT_STATUSES = {"FREE", "OCCUPIED", "RESERVED", "MAINTENANCE"}


def default_parking_spots() -> list[dict[str, str]]:
    """Return the standard SmartPark layout used on a new installation."""
    layout = (("A", "Ground", 16), ("B", "Ground", 16), ("C", "Level 1", 8))
    return [
        {"number": f"{zone}-{index:02d}", "zone": zone, "floor": floor}
        for zone, floor, count in layout
        for index in range(1, count + 1)
    ]


def seed_default_parking_spots(db: Session) -> int:
    """Add missing default spots without changing spots already configured."""
    existing_numbers = {number for (number,) in db.query(ParkingSpot.number).all()}
    new_spots = [
        ParkingSpot(**spot, status="FREE")
        for spot in default_parking_spots()
        if spot["number"] not in existing_numbers
    ]
    if new_spots:
        db.add_all(new_spots)
        db.commit()
    return len(new_spots)
