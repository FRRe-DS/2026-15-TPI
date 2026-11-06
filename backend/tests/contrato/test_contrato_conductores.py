"""T099: las respuestas de los tres endpoints de conductores cumplen el contrato."""

from __future__ import annotations

from collections.abc import Callable

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


def _crear_conductor(
    cliente: TestClient,
    headers: dict[str, str],
    **cambios: str,
) -> httpx.Response:
    datos = {**CONDUCTOR, **cambios}
    return cliente.post("/api/v1/conductores", json=datos, headers=headers)


def test_crear_conductor_cumple_el_contrato(
    cliente: TestClient,
    headers_conductor: dict[str, str],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    respuesta = _crear_conductor(cliente, headers_conductor)
    assert respuesta.status_code == 201, respuesta.text
    validar_contrato(respuesta)

    creado = respuesta.json()
    assert isinstance(creado["id"], int)
    assert creado["dni"] == CONDUCTOR["dni"]
    assert creado["nombre"] == CONDUCTOR["nombre"]
    assert creado["apellido"] == CONDUCTOR["apellido"]
    assert creado["telefono"] == CONDUCTOR["telefono"]
    assert creado["email"] == CONDUCTOR["email"]
    assert creado["habilitacion"] == "PENDIENTE"
    assert creado["conectado"] is False
    assert creado["disponible"] is False
    assert creado["documentos"] == []
    assert creado["vehiculos"] == []
    assert respuesta.headers["location"] == f"/api/v1/conductores/{creado['id']}"


def test_listar_conductores_cumple_el_contrato(
    cliente: TestClient,
    headers_conductor: dict[str, str],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    creado = _crear_conductor(cliente, headers_conductor).json()

    respuesta = cliente.get("/api/v1/conductores", headers=headers_conductor)
    assert respuesta.status_code == 200, respuesta.text
    validar_contrato(respuesta)

    listado = respuesta.json()
    assert isinstance(listado, list)
    assert creado["id"] in [conductor["id"] for conductor in listado]

    encontrado = next(conductor for conductor in listado if conductor["id"] == creado["id"])
    assert encontrado["dni"] == CONDUCTOR["dni"]
    assert encontrado["latitud"] is None
    assert encontrado["longitud"] is None
    assert encontrado["fecha_act_ubic"] is None


def test_listar_conductores_filtra_por_habilitacion(
    cliente: TestClient,
    headers_conductor: dict[str, str],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    creado = _crear_conductor(cliente, headers_conductor).json()

    habilitados = cliente.get(
        "/api/v1/conductores",
        params={"habilitado": "true"},
        headers=headers_conductor,
    )
    assert habilitados.status_code == 200, habilitados.text
    validar_contrato(habilitados)
    assert habilitados.json() == []

    pendientes = cliente.get(
        "/api/v1/conductores",
        params={"habilitado": "false"},
        headers=headers_conductor,
    )
    assert pendientes.status_code == 200, pendientes.text
    validar_contrato(pendientes)
    assert creado["id"] in [conductor["id"] for conductor in pendientes.json()]


def test_obtener_conductor_cumple_el_contrato(
    cliente: TestClient,
    headers_conductor: dict[str, str],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    creado = _crear_conductor(cliente, headers_conductor).json()

    respuesta = cliente.get(
        f"/api/v1/conductores/{creado['id']}",
        headers=headers_conductor,
    )
    assert respuesta.status_code == 200, respuesta.text
    validar_contrato(respuesta)

    detalle = respuesta.json()
    assert detalle["id"] == creado["id"]
    assert detalle["dni"] == CONDUCTOR["dni"]
    assert detalle["documentos"] == []
    assert detalle["vehiculos"] == []
    assert detalle["latitud"] is None
    assert detalle["longitud"] is None
    assert detalle["fecha_act_ubic"] is None
