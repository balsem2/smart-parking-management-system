from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(tags=["system"])

@router.get("/")
def root(): return {"message": "Welcome to SmartPark AI API"}

@router.get("/health")
def health_check(): return {"status": "healthy", "service": "SmartPark AI API"}

@router.get("/db-test")
def db_test(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "success", "message": "Database connected successfully"}
