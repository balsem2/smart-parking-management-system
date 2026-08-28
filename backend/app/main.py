import asyncio
import os
from pathlib import Path
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.core.database import SessionLocal
from app.core.schema import ensure_customer_account_schema
import app.models
from app.routes import (
    analytics,
    monitoring,
    parking,
    payments,
    reservations,
    realtime,
    system,
    smart_parking,
    users,
    vehicles,
)
from app.services.realtime import (
    close_redis_connection,
    listen_for_dashboard_events,
)
from app.services.parking_spots import seed_default_parking_spots
from app.services.monitoring import create_reservation_time_exceeded_alerts
from app.services.realtime import publish_dashboard_event


async def monitor_reservation_overtime() -> None:
    """Periodically create and broadcast alerts for overstaying reservations."""
    interval_seconds = max(15, int(os.getenv("RESERVATION_MONITOR_INTERVAL_SECONDS", "60")))
    while True:
        db = SessionLocal()
        try:
            alerts = create_reservation_time_exceeded_alerts(db)
            db.commit()
            for alert in alerts:
                await publish_dashboard_event({
                    "type": "alert_created",
                    "alert_id": alert.id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "vehicle_id": alert.vehicle_id,
                    "parking_session_id": alert.parking_session_id,
                })
        finally:
            db.close()
        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Populate the initial parking map only with spots that do not already exist.
    # Existing installations keep all of their current configuration unchanged.
    db = SessionLocal()
    try:
        seed_default_parking_spots(db)
    finally:
        db.close()

    listener_task = asyncio.create_task(listen_for_dashboard_events())
    reservation_monitor_task = asyncio.create_task(monitor_reservation_overtime())

    yield

    listener_task.cancel()
    reservation_monitor_task.cancel()

    for task in (listener_task, reservation_monitor_task):
        with suppress(asyncio.CancelledError):
            await task

    await close_redis_connection()


app = FastAPI(
    title="SmartPark AI API",
    version="1.0.0",
    lifespan=lifespan,
)

UPLOADS_DIR = Path(__file__).resolve().parents[1] / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


for route_module in (
    system,
    smart_parking,
    vehicles,
    parking,
    reservations,
    realtime,
    users,
    payments,
    monitoring,
    analytics,
):
    app.include_router(route_module.router)


Base.metadata.create_all(bind=engine)
ensure_customer_account_schema(engine)


@app.get("/")
def root():
    return {
        "message": "Welcome to SmartPark AI API"
    }
