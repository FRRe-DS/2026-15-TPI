"""Aplicación FastAPI del módulo M3."""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import Depends, FastAPI
from fastapi.routing import APIRouter

from app.api.errores import registrar_manejadores
from app.api.routers import (
    conductores,
    documentacion,
    habilitacion,
    vehiculos,
    vehiculos_habilitacion,
)
from app.api.seguridad import requerir_usuario

# Cada PR del Stack 2 suma sus routers a esta lista.
ROUTERS: tuple[APIRouter, ...] = (
    conductores.router,
    habilitacion.router,
    documentacion.router,
    vehiculos.router,
    vehiculos_habilitacion.router,
)


def crear_app(*, routers: Sequence[APIRouter] | None = None) -> FastAPI:
    """Crea la aplicación con el prefijo, la seguridad y los errores comunes."""
    app = FastAPI(
        title="API M3 - Conductores y Vehículos",
        version="1.0.0",
    )
    registrar_manejadores(app)

    @app.get("/salud", include_in_schema=False)
    def salud() -> dict[str, str]:
        """Sonda de salud usada por Docker Compose."""
        return {"estado": "ok"}

    for router in ROUTERS if routers is None else routers:
        app.include_router(
            router,
            prefix="/api/v1",
            dependencies=[Depends(requerir_usuario)],
        )

    return app


app = crear_app()
