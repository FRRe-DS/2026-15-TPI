
from fastapi import FastAPI

from app.api.rutas_prueba import router

app = FastAPI(
    title="API M3 - Conductores y Vehículos",
    version="1.0.0",
)

app.include_router(router, prefix="/api/v1")