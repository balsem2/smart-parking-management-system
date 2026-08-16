from fastapi import APIRouter

from api.routes import analytics, monitoring, parking, payments, reservations, system, users, vehicles

api_router = APIRouter()
for route_module in (system, vehicles, parking, reservations, users, payments, monitoring, analytics):
    api_router.include_router(route_module.router)
