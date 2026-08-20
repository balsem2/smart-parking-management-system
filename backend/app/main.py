import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.routes import (
    analytics,
    monitoring,
    parking,
    payments,
    reservations,
    realtime,
    system,
    users,
    vehicles,
)
from app.services.realtime import (
    close_redis_connection,
    listen_for_dashboard_events,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


for route_module in (
    system,
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


@app.get("/")
def root():
    return {
        "message": "Welcome to SmartPark AI API"
    }
