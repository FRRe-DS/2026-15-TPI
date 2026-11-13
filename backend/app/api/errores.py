"""Manejo uniforme de errores de la API.

Todas las respuestas de error usan ``{"codigo": "...", "mensaje": "..."}``
según ``specs/iteracion1/contracts/errores.md``.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.dominio.errores import (
    AccesoProhibido,
    ConductorNoHabilitado,
    DatosInvalidos,
    DniDuplicado,
    LicenciaVigenteRequerida,
    NoEncontrado,
    PatenteDuplicada,
    RolNoAutorizado,
    SolicitudVencida,
    SolicitudYaRespondida,
    TransicionInvalida,
)

logger = logging.getLogger(__name__)

# (excepción de dominio, HTTP, codigo del catálogo)
MAPEO_ERRORES_DOMINIO: tuple[tuple[type[Exception], int, str], ...] = (
    (NoEncontrado, 404, "NO_ENCONTRADO"),
    (DniDuplicado, 409, "DNI_DUPLICADO"),
    (PatenteDuplicada, 409, "PATENTE_DUPLICADA"),
    (TransicionInvalida, 409, "TRANSICION_INVALIDA"),
    (LicenciaVigenteRequerida, 422, "LICENCIA_VIGENTE_REQUERIDA"),
    (DatosInvalidos, 422, "DATOS_INVALIDOS"),
    (AccesoProhibido, 403, "ACCESO_PROHIBIDO"),
    (RolNoAutorizado, 403, "SIN_PERMISOS"),
    (SolicitudYaRespondida, 409, "SOLICITUD_YA_RESPONDIDA"),
    (SolicitudVencida, 410, "SOLICITUD_VENCIDA"),
    (ConductorNoHabilitado, 422, "CONDUCTOR_NO_HABILITADO"),
)


class ErrorAPI(Exception):
    """Error de la capa HTTP con su código del catálogo."""

    def __init__(
        self,
        status_code: int,
        codigo: str,
        mensaje: str,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.codigo = codigo
        self.mensaje = mensaje
        self.headers = dict(headers) if headers is not None else None
        super().__init__(mensaje)


def no_autenticado() -> ErrorAPI:
    return ErrorAPI(401, "NO_AUTENTICADO", "Token ausente o inválido")


def sin_permisos(mensaje: str) -> ErrorAPI:
    return ErrorAPI(403, "SIN_PERMISOS", mensaje)


def limite_de_solicitudes(retry_after: int) -> ErrorAPI:
    return ErrorAPI(
        429,
        "LIMITE_DE_SOLICITUDES",
        "Se alcanzó el límite de solicitudes; reintente más tarde.",
        headers={"Retry-After": str(retry_after), "Cache-Control": "no-store"},
    )


def servicio_temporalmente_no_disponible() -> ErrorAPI:
    return ErrorAPI(
        503,
        "SERVICIO_TEMPORALMENTE_NO_DISPONIBLE",
        "El servicio no está disponible temporalmente.",
    )


def cuerpo_error(codigo: str, mensaje: str) -> dict[str, str]:
    return {"codigo": codigo, "mensaje": mensaje}


def respuesta_error(status_code: int, codigo: str, mensaje: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=cuerpo_error(codigo, mensaje),
    )


async def manejar_error_api(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ErrorAPI)
    return JSONResponse(
        status_code=exc.status_code,
        content=cuerpo_error(exc.codigo, exc.mensaje),
        headers=exc.headers,
    )


def _manejar_error_dominio(status_code: int, codigo: str):
    async def manejador(_: Request, exc: Exception) -> JSONResponse:
        return respuesta_error(status_code, codigo, str(exc))

    return manejador


async def manejar_validacion(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return respuesta_error(
        400,
        "SOLICITUD_INVALIDA",
        "La solicitud no cumple el formato esperado",
    )


async def manejar_http(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    if isinstance(exc.detail, dict) and "codigo" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    codigos = {
        401: "NO_AUTENTICADO",
        403: "SIN_PERMISOS",
        404: "NO_ENCONTRADO",
    }
    codigo = codigos.get(exc.status_code, "SOLICITUD_INVALIDA")
    return respuesta_error(exc.status_code, codigo, str(exc.detail))


async def manejar_inesperado(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error inesperado al procesar la solicitud", exc_info=exc)
    return respuesta_error(500, "ERROR_INTERNO", "Ocurrió un error interno")


def registrar_manejadores(app: FastAPI) -> None:
    """Registra los manejadores de excepciones en la aplicación."""
    app.add_exception_handler(ErrorAPI, manejar_error_api)
    app.add_exception_handler(RequestValidationError, manejar_validacion)
    app.add_exception_handler(StarletteHTTPException, manejar_http)
    for excepcion, status_code, codigo in MAPEO_ERRORES_DOMINIO:
        app.add_exception_handler(excepcion, _manejar_error_dominio(status_code, codigo))
    app.add_exception_handler(Exception, manejar_inesperado)
