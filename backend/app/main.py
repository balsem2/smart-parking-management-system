from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.routers import alerts, analytics, events, parking, reservations, vehicles
from app.seed import seed_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API métier du système de gestion de parking SmartPark AI.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    vehicles.router,
    parking.router,
    reservations.router,
    events.router,
    alerts.router,
    analytics.router,
):
    app.include_router(router, prefix=settings.api_prefix)


@app.get("/", tags=["system"])
def root():
    return {"name": settings.app_name, "docs": "/docs", "api": settings.api_prefix}


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "healthy", "service": settings.app_name}
