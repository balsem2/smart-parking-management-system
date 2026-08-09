from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Alert
from app.schemas import AlertRead

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertRead])
def list_alerts(unacknowledged_only: bool = False, db: Session = Depends(get_db)):
    query = select(Alert).order_by(Alert.created_at.desc())
    if unacknowledged_only:
        query = query.where(Alert.acknowledged_at.is_(None))
    return db.scalars(query).all()


@router.post("/{alert_id}/acknowledge", response_model=AlertRead)
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert
