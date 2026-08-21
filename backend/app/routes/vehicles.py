from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.authorization import require_roles
from app.models.vehicle import Vehicle
from app.models.vehicle_image import VehicleImage

router = APIRouter(tags=["vehicles"])
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads" / "vehicles"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}

@router.post("/vehicles")
def create_vehicle(vehicle: dict, db: Session = Depends(get_db), current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR"))):
    plate_number = vehicle.get("plate_number", "").strip().upper()
    status = vehicle.get("status", "VISITOR").upper()
    if not plate_number:
        raise HTTPException(status_code=422, detail="plate_number is required")
    if status not in {"AUTHORIZED", "VISITOR", "VIP", "BLACKLISTED"}:
        raise HTTPException(status_code=422, detail="Invalid vehicle status")
    if db.query(Vehicle).filter(Vehicle.plate_number == plate_number).first():
        raise HTTPException(status_code=409, detail="A vehicle with this plate already exists")
    new_vehicle = Vehicle(plate_number=plate_number, owner_name=vehicle.get("owner_name"), owner_phone=vehicle.get("owner_phone"), type=vehicle.get("type"), brand=vehicle.get("brand"), model=vehicle.get("model"), color=vehicle.get("color"), status=status)
    db.add(new_vehicle); db.commit(); db.refresh(new_vehicle)
    return {"message": "Vehicle created successfully", "id": new_vehicle.id, "plate_number": new_vehicle.plate_number}

@router.get("/vehicles")
def get_vehicles(db: Session = Depends(get_db), current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR", "SECURITY"))): return db.query(Vehicle).all()


@router.post("/vehicles/{vehicle_id}/images")
async def upload_vehicle_image(
    vehicle_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR")),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG and WebP images are supported")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Image file is empty")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be smaller than 10 MB")

    extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[file.content_type]
    stored_name = f"{uuid4().hex}{extension}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    destination = UPLOAD_DIR / stored_name
    destination.write_bytes(content)

    image = VehicleImage(
        vehicle_id=vehicle.id,
        file_path=f"/uploads/vehicles/{stored_name}",
        original_filename=file.filename,
        content_type=file.content_type,
        source="UPLOAD",
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


@router.get("/vehicles/{vehicle_id}/images")
def get_vehicle_images(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR", "SECURITY")),
):
    if not db.query(Vehicle).filter(Vehicle.id == vehicle_id).first():
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return db.query(VehicleImage).filter(VehicleImage.vehicle_id == vehicle_id).all()


@router.delete("/vehicles/{vehicle_id}/images/{image_id}")
def delete_vehicle_image(
    vehicle_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("SUPER_ADMIN", "ADMIN")),
):
    image = db.query(VehicleImage).filter(
        VehicleImage.id == image_id,
        VehicleImage.vehicle_id == vehicle_id,
    ).first()
    if not image:
        raise HTTPException(status_code=404, detail="Vehicle image not found")

    file_path = Path(__file__).resolve().parents[2] / image.file_path.lstrip("/")
    if file_path.exists():
        file_path.unlink()
    db.delete(image)
    db.commit()
    return {"message": "Vehicle image deleted successfully"}
