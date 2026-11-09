"""Aplicación FastAPI del módulo M3."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.routing import APIRouter
from redis import Redis

from app.api.configuracion import obtener_configuracion
from app.api.errores import registrar_manejadores
from app.api.rate_limit import RedisRateLimiter
from app.api.routers import (
    conductores,
    documentacion,
    estado,
    habilitacion,
    solicitudes,
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
    estado.router,
    solicitudes.router,
)


def crear_app(*, routers: Sequence[APIRouter] | None = None) -> FastAPI:
    """Crea la aplicación con el prefijo, la seguridad y los errores comunes."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        settings = getattr(app.state, "settings", None)
        if settings is None:
            settings = obtener_configuracion()
            app.state.settings = settings
        cliente_redis = Redis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD.get_secret_value() or None,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        app.state.rate_limiter = RedisRateLimiter(cliente_redis)
        try:
            yield
        finally:
            cliente_redis.close()

    app = FastAPI(
        title="API M3 - Conductores y Vehículos",
        version="1.2.0",
        lifespan=lifespan,
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
