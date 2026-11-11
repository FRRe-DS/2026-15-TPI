"""T100: contrato de consulta y acción de habilitación del conductor."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def _url_habilitacion(id_conductor: int) -> str:
    return f"/api/v1/conductores/{id_conductor}/habilitacion"


def test_consultar_habilitacion_inicial_cumple_el_contrato(
    cliente: TestClient,
    headers_operador: dict[str, str],
    crear_conductor: Callable[..., dict[str, Any]],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    conductor = crear_conductor()

    respuesta = cliente.get(
        _url_habilitacion(conductor["id"]),
        headers=headers_operador,
    )
    assert respuesta.status_code == 200, respuesta.text
    validar_contrato(respuesta)

    cuerpo = respuesta.json()
    assert cuerpo["id_conductor"] == conductor["id"]
    assert cuerpo["estado"] == "PENDIENTE"
    assert len(cuerpo["historial"]) == 1

    alta = cuerpo["historial"][0]
    assert alta["estado"] == "PENDIENTE"
    assert alta["motivo"] == "Alta del conductor"
    assert alta["id_operador"] is None
    assert alta["fecha"]


def test_aprobar_habilitacion_cumple_el_contrato(
    cliente: TestClient,
    headers_operador: dict[str, str],
    crear_conductor: Callable[..., dict[str, Any]],
    registrar_licencia: Callable[..., httpx.Response],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    conductor = crear_conductor()
    licencia = registrar_licencia(conductor["id"])
    assert licencia.status_code == 201, licencia.text

    respuesta = cliente.post(
        _url_habilitacion(conductor["id"]),
        json={
            "accion": "APROBAR",
            "motivo": "Licencia vigente y documentación completa",
        },
        headers=headers_operador,
    )
    assert respuesta.status_code == 200, respuesta.text
    validar_contrato(respuesta)

    cuerpo = respuesta.json()
    assert cuerpo["id_conductor"] == conductor["id"]
    assert cuerpo["estado"] == "APROBADA"
    assert len(cuerpo["eventos"]) == 2

    alta, aprobacion = cuerpo["eventos"]
    assert alta["accion"] == "ALTA"
    assert alta["estado_anterior"] is None
    assert alta["estado_nuevo"] == "PENDIENTE"
    assert alta["id_operador"] is None

    assert aprobacion["accion"] == "APROBAR"
    assert aprobacion["estado_anterior"] == "PENDIENTE"
    assert aprobacion["estado_nuevo"] == "APROBADA"
    assert aprobacion["motivo"] == "Licencia vigente y documentación completa"
    assert aprobacion["id_operador"] == 7
    assert aprobacion["fecha"]

    consulta = cliente.get(
        _url_habilitacion(conductor["id"]),
        headers=headers_operador,
    )
    assert consulta.status_code == 200, consulta.text
    validar_contrato(consulta)

    resumen = consulta.json()
    assert resumen["estado"] == "APROBADA"
    assert [item["estado"] for item in resumen["historial"]] == ["PENDIENTE", "APROBADA"]
    assert resumen["historial"][-1]["id_operador"] == 7


def test_observar_habilitacion_cumple_el_contrato(
    cliente: TestClient,
    headers_operador: dict[str, str],
    crear_conductor: Callable[..., dict[str, Any]],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    conductor = crear_conductor()

    respuesta = cliente.post(
        _url_habilitacion(conductor["id"]),
        json={
            "accion": "OBSERVAR",
            "motivo": "Falta documentación complementaria",
        },
        headers=headers_operador,
    )
    assert respuesta.status_code == 200, respuesta.text
    validar_contrato(respuesta)

    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "OBSERVADA"
    evento = cuerpo["eventos"][-1]
    assert evento["accion"] == "OBSERVAR"
    assert evento["estado_anterior"] == "PENDIENTE"
    assert evento["estado_nuevo"] == "OBSERVADA"
    assert evento["id_operador"] == 7
