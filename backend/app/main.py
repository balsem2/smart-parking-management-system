import asyncio
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


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Populate the initial parking map only with spots that do not already exist.
    # Existing installations keep all of their current configuration unchanged.
    db = SessionLocal()
    try:
        seed_default_parking_spots(db)
    finally:
        db.close()

    listener_task = asyncio.create_task(
        listen_for_dashboard_events()
    )

    yield

    listener_task.cancel()

    with suppress(asyncio.CancelledError):
        await listener_task

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
