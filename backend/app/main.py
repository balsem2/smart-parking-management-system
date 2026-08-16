from fastapi import FastAPI

from api.router import api_router
from core.database import Base, engine

app = FastAPI(title="SmartPark AI API", version="1.0.0")
app.include_router(api_router)
Base.metadata.create_all(bind=engine)
