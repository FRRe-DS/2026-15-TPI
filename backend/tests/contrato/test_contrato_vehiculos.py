"""T102: contrato de alta, listado, detalle y habilitación de vehículos."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def _url_vehiculos(id_conductor: int) -> str:
    return f"/api/v1/conductores/{id_conductor}/vehiculos"


def test_crear_vehiculo_cumple_el_contrato(
    crear_conductor: Callable[..., dict[str, Any]],
    crear_vehiculo: Callable[..., httpx.Response],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    conductor = crear_conductor()

    respuesta = crear_vehiculo(conductor["id"])
    assert respuesta.status_code == 201, respuesta.text
    validar_contrato(respuesta)

    creado = respuesta.json()
    assert isinstance(creado["id"], int)
    assert creado["id_conductor"] == conductor["id"]
    assert creado["tipo"] == "AUTO"
    assert creado["patente"] == "AB123CD"
    assert creado["marca"] == "Toyota"
    assert creado["modelo"] == "Corolla"
    assert creado["anio"] == 2022
    assert creado["tipos_serv"] == [{"tipo": "PASAJEROS", "habilitado": False}]
    assert creado["documentos"] == []
    assert creado["habilitacion"] == "PENDIENTE"
    assert respuesta.headers["location"] == (
        f"/api/v1/conductores/{conductor['id']}/vehiculos/{creado['id']}"
    )


def test_listar_vehiculos_cumple_el_contrato(
    cliente: TestClient,
    headers_conductor: dict[str, str],
    crear_conductor: Callable[..., dict[str, Any]],
    crear_vehiculo: Callable[..., httpx.Response],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    conductor = crear_conductor()

    primero = crear_vehiculo(conductor["id"])
    assert primero.status_code == 201, primero.text
    segundo = crear_vehiculo(
        conductor["id"],
        tipo="MOTO",
        patente="MOTO123",
        marca="Honda",
        modelo="CG 150",
        anio=2024,
        tipos_serv=["ENVIOS"],
    )
    assert segundo.status_code == 201, segundo.text

    respuesta = cliente.get(_url_vehiculos(conductor["id"]), headers=headers_conductor)
    assert respuesta.status_code == 200, respuesta.text
    validar_contrato(respuesta)

    listado = respuesta.json()
    assert [vehiculo["id"] for vehiculo in listado] == [
        primero.json()["id"],
        segundo.json()["id"],
    ]
    assert [vehiculo["patente"] for vehiculo in listado] == ["AB123CD", "MOTO123"]
    assert [vehiculo["habilitacion"] for vehiculo in listado] == ["PENDIENTE", "PENDIENTE"]

    motos = cliente.get(
        _url_vehiculos(conductor["id"]),
        params={"tipo": "MOTO"},
        headers=headers_conductor,
    )
    assert motos.status_code == 200, motos.text
    validar_contrato(motos)
    assert [vehiculo["patente"] for vehiculo in motos.json()] == ["MOTO123"]

    pendientes = cliente.get(
        _url_vehiculos(conductor["id"]),
        params={"habilitacion": "PENDIENTE"},
        headers=headers_conductor,
    )
    assert pendientes.status_code == 200, pendientes.text
    validar_contrato(pendientes)
    assert [vehiculo["id"] for vehiculo in pendientes.json()] == [
        primero.json()["id"],
        segundo.json()["id"],
    ]


def test_obtener_vehiculo_cumple_el_contrato(
    cliente: TestClient,
    headers_conductor: dict[str, str],
    crear_conductor: Callable[..., dict[str, Any]],
    crear_vehiculo: Callable[..., httpx.Response],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    conductor = crear_conductor()
    creado = crear_vehiculo(conductor["id"])
    assert creado.status_code == 201, creado.text
    id_vehiculo = creado.json()["id"]

    respuesta = cliente.get(
        f"{_url_vehiculos(conductor['id'])}/{id_vehiculo}",
        headers=headers_conductor,
    )
    assert respuesta.status_code == 200, respuesta.text
    validar_contrato(respuesta)

    detalle = respuesta.json()
    assert detalle["id"] == id_vehiculo
    assert detalle["id_conductor"] == conductor["id"]
    assert detalle["patente"] == "AB123CD"
    assert detalle["tipo"] == "AUTO"
    assert detalle["tipos_serv"] == [{"tipo": "PASAJEROS", "habilitado": False}]
    assert detalle["documentos"] == []
    assert detalle["habilitacion"] == "PENDIENTE"


def test_habilitar_vehiculo_cumple_el_contrato(
    cliente: TestClient,
    headers_conductor: dict[str, str],
    headers_operador: dict[str, str],
    crear_conductor: Callable[..., dict[str, Any]],
    crear_vehiculo: Callable[..., httpx.Response],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    conductor = crear_conductor()
    creado = crear_vehiculo(conductor["id"])
    assert creado.status_code == 201, creado.text
    id_vehiculo = creado.json()["id"]

    respuesta = cliente.post(
        f"{_url_vehiculos(conductor['id'])}/{id_vehiculo}/habilitacion",
        json={
            "accion": "APROBAR",
            "motivo": "Documentación del vehículo validada",
        },
        headers=headers_operador,
    )
    assert respuesta.status_code == 200, respuesta.text
    validar_contrato(respuesta)

    resultado = respuesta.json()
    assert resultado["id_vehiculo"] == id_vehiculo
    assert resultado["estado"] == "APROBADA"
    assert len(resultado["eventos"]) == 2

    alta, aprobacion = resultado["eventos"]
    assert alta["accion"] == "ALTA"
    assert alta["estado_anterior"] is None
    assert alta["estado_nuevo"] == "PENDIENTE"
    assert alta["motivo"] == "Alta del vehiculo"
    assert alta["id_operador"] is None

    assert aprobacion["accion"] == "APROBAR"
    assert aprobacion["estado_anterior"] == "PENDIENTE"
    assert aprobacion["estado_nuevo"] == "APROBADA"
    assert aprobacion["motivo"] == "Documentación del vehículo validada"
    assert aprobacion["id_operador"] == 7
    assert aprobacion["fecha"]

    detalle = cliente.get(
        f"{_url_vehiculos(conductor['id'])}/{id_vehiculo}",
        headers=headers_conductor,
    )
    assert detalle.status_code == 200, detalle.text
    validar_contrato(detalle)
    assert detalle.json()["habilitacion"] == "APROBADA"

    aprobados = cliente.get(
        _url_vehiculos(conductor["id"]),
        params={"habilitacion": "APROBADA"},
        headers=headers_conductor,
    )
    assert aprobados.status_code == 200, aprobados.text
    validar_contrato(aprobados)
    assert [vehiculo["id"] for vehiculo in aprobados.json()] == [id_vehiculo]

    pendientes = cliente.get(
        _url_vehiculos(conductor["id"]),
        params={"habilitacion": "PENDIENTE"},
        headers=headers_conductor,
    )
    assert pendientes.status_code == 200, pendientes.text
    validar_contrato(pendientes)
    assert pendientes.json() == []
