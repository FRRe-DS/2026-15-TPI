"""T103: los errores de la API cumplen el formato ``{codigo, mensaje}``."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

CONDUCTOR = {
    "dni": "30123456",
    "nombre": "Ana",
    "apellido": "Gómez",
    "telefono": "+5491176543210",
    "email": "ana.gomez@example.com",
}


def _verificar_error(
    respuesta: httpx.Response,
    status_code: int,
    codigo: str,
    validar: Callable[[httpx.Response], None],
) -> None:
    assert respuesta.status_code == status_code, respuesta.text
    validar(respuesta)

    cuerpo = respuesta.json()
    assert set(cuerpo) == {"codigo", "mensaje"}
    assert cuerpo["codigo"] == codigo
    assert isinstance(cuerpo["mensaje"], str)
    assert cuerpo["mensaje"].strip()


def test_sin_token_responde_401(
    cliente: TestClient,
    validar_respuesta: Callable[[httpx.Response], None],
) -> None:
    respuesta = cliente.get("/api/v1/conductores")

    _verificar_error(respuesta, 401, "NO_AUTENTICADO", validar_respuesta)


def test_conductor_no_puede_accionar_habilitacion_responde_403(
    cliente: TestClient,
    headers_conductor_de: Callable[[int], dict[str, str]],
    crear_conductor: Callable[..., dict[str, Any]],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    conductor = crear_conductor()

    respuesta = cliente.post(
        f"/api/v1/conductores/{conductor['id']}/habilitacion",
        json={"accion": "APROBAR", "motivo": "Intento sin permisos"},
        headers=headers_conductor_de(conductor["id"]),
    )

    _verificar_error(respuesta, 403, "SIN_PERMISOS", validar_contrato)


def test_recurso_inexistente_responde_404(
    cliente: TestClient,
    headers_conductor: dict[str, str],
    crear_conductor: Callable[..., dict[str, Any]],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    conductores = cliente.get("/api/v1/conductores/999999", headers=headers_conductor)
    _verificar_error(conductores, 404, "NO_ENCONTRADO", validar_contrato)

    conductor = crear_conductor()
    vehiculo = cliente.get(
        f"/api/v1/conductores/{conductor['id']}/vehiculos/999999",
        headers=headers_conductor,
    )
    _verificar_error(vehiculo, 404, "NO_ENCONTRADO", validar_contrato)


def test_dni_duplicado_responde_409(
    cliente: TestClient,
    headers_conductor: dict[str, str],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    primera = cliente.post("/api/v1/conductores", json=CONDUCTOR, headers=headers_conductor)
    assert primera.status_code == 201, primera.text

    segunda = cliente.post("/api/v1/conductores", json=CONDUCTOR, headers=headers_conductor)

    _verificar_error(segunda, 409, "DNI_DUPLICADO", validar_contrato)


def test_patente_duplicada_responde_409(
    crear_conductor: Callable[..., dict[str, Any]],
    crear_vehiculo: Callable[..., httpx.Response],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    conductor = crear_conductor()
    primera = crear_vehiculo(conductor["id"])
    assert primera.status_code == 201, primera.text

    segunda = crear_vehiculo(conductor["id"])

    _verificar_error(segunda, 409, "PATENTE_DUPLICADA", validar_contrato)


def test_transicion_invalida_responde_409(
    cliente: TestClient,
    headers_operador: dict[str, str],
    crear_conductor: Callable[..., dict[str, Any]],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    conductor = crear_conductor()

    respuesta = cliente.post(
        f"/api/v1/conductores/{conductor['id']}/habilitacion",
        json={"accion": "SUSPENDER", "motivo": "No está permitido desde PENDIENTE"},
        headers=headers_operador,
    )

    _verificar_error(respuesta, 409, "TRANSICION_INVALIDA", validar_contrato)


def test_aprobar_sin_licencia_vigente_responde_422(
    cliente: TestClient,
    headers_operador: dict[str, str],
    crear_conductor: Callable[..., dict[str, Any]],
    registrar_licencia: Callable[..., httpx.Response],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    conductor = crear_conductor()
    licencia = registrar_licencia(
        conductor["id"],
        fecha_emision="2020-01-01",
        fecha_vencimiento="2021-01-01",
    )
    assert licencia.status_code == 201, licencia.text

    respuesta = cliente.post(
        f"/api/v1/conductores/{conductor['id']}/habilitacion",
        json={"accion": "APROBAR", "motivo": "Intento con licencia vencida"},
        headers=headers_operador,
    )

    _verificar_error(respuesta, 422, "LICENCIA_VIGENTE_REQUERIDA", validar_contrato)


def test_datos_invalidos_responde_422(
    crear_conductor: Callable[..., dict[str, Any]],
    registrar_licencia: Callable[..., httpx.Response],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    conductor = crear_conductor()

    respuesta = registrar_licencia(
        conductor["id"],
        fecha_emision="2028-01-01",
        fecha_vencimiento="2027-01-01",
    )

    _verificar_error(respuesta, 422, "DATOS_INVALIDOS", validar_contrato)
