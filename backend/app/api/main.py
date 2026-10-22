"""Aplicación FastAPI mínima usada por el stack de infraestructura.

Los endpoints de negocio pertenecen al Stack 2. Aquí sólo se expone un
chequeo de salud para que Docker Compose pueda esperar a la API sin acoplar
el arranque de la base ni de Keycloak.
"""

from __future__ import annotations

from fastapi import FastAPI


def crear_app() -> FastAPI:
    app = FastAPI(title="M3 - Conductores y Vehículos", version="0.1.0")

    @app.get("/salud", tags=["infra"])
    def salud() -> dict[str, str]:
        return {"estado": "ok", "servicio": "m3"}

    @app.get("/api/v1/salud", tags=["infra"])
    def salud_api() -> dict[str, str]:
        return {"estado": "ok", "servicio": "m3"}

    return app


app = crear_app()
