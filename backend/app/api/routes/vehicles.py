from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from models.vehicle import Vehicle

router = APIRouter(tags=["vehicles"])

@router.post("/vehicles")
def create_vehicle(vehicle: dict, db: Session = Depends(get_db)):
    new_vehicle = Vehicle(plate_number=vehicle["plate_number"], owner_name=vehicle.get("owner_name"), owner_phone=vehicle.get("owner_phone"), type=vehicle.get("type"), brand=vehicle.get("brand"), model=vehicle.get("model"), color=vehicle.get("color"), status=vehicle["status"])
    db.add(new_vehicle); db.commit(); db.refresh(new_vehicle)
    return {"message": "Vehicle created successfully", "id": new_vehicle.id, "plate_number": new_vehicle.plate_number}

@router.get("/vehicles")
def get_vehicles(db: Session = Depends(get_db)): return db.query(Vehicle).all()
