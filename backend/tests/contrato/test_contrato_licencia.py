"""T101: contrato del registro de licencia del conductor."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_registrar_licencia_vigente_cumple_el_contrato(
    cliente: TestClient,
    headers_conductor: dict[str, str],
    crear_conductor: Callable[..., dict[str, Any]],
    registrar_licencia: Callable[..., httpx.Response],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    conductor = crear_conductor()

    respuesta = registrar_licencia(conductor["id"])
    assert respuesta.status_code == 201, respuesta.text
    validar_contrato(respuesta)

    documento = respuesta.json()
    assert documento["id_conductor"] == conductor["id"]
    assert documento["tipo"] == "LICENCIA"
    assert documento["numero"] == "LIC-12345678"
    assert documento["categoria"] == "B1"
    assert documento["fecha_emision"] == "2024-05-10"
    assert documento["fecha_vencimiento"] == "2028-05-10"
    assert documento["estado"] == "VIGENTE"

    detalle = cliente.get(
        f"/api/v1/conductores/{conductor['id']}",
        headers=headers_conductor,
    )
    assert detalle.status_code == 200, detalle.text
    validar_contrato(detalle)

    documentos = detalle.json()["documentos"]
    assert len(documentos) == 1
    assert documentos[0]["numero"] == documento["numero"]
    assert documentos[0]["estado"] == "VIGENTE"


def test_registrar_licencia_vencida_cumple_el_contrato(
    crear_conductor: Callable[..., dict[str, Any]],
    registrar_licencia: Callable[..., httpx.Response],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    conductor = crear_conductor()

    respuesta = registrar_licencia(
        conductor["id"],
        fecha_emision="2020-01-01",
        fecha_vencimiento="2021-01-01",
    )
    assert respuesta.status_code == 201, respuesta.text
    validar_contrato(respuesta)

    documento = respuesta.json()
    assert documento["id_conductor"] == conductor["id"]
    assert documento["fecha_vencimiento"] == "2021-01-01"
    assert documento["estado"] == "VENCIDO"


def test_registrar_varias_licencias_cumple_el_contrato(
    cliente: TestClient,
    headers_conductor: dict[str, str],
    crear_conductor: Callable[..., dict[str, Any]],
    registrar_licencia: Callable[..., httpx.Response],
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    conductor = crear_conductor()

    vencida = registrar_licencia(
        conductor["id"],
        numero="LIC-VENCIDA",
        fecha_emision="2020-01-01",
        fecha_vencimiento="2021-01-01",
    )
    assert vencida.status_code == 201, vencida.text
    validar_contrato(vencida)

    vigente = registrar_licencia(conductor["id"], numero="LIC-VIGENTE")
    assert vigente.status_code == 201, vigente.text
    validar_contrato(vigente)

    detalle = cliente.get(
        f"/api/v1/conductores/{conductor['id']}",
        headers=headers_conductor,
    )
    assert detalle.status_code == 200, detalle.text
    validar_contrato(detalle)

    documentos = detalle.json()["documentos"]
    assert [documento["numero"] for documento in documentos] == [
        "LIC-VENCIDA",
        "LIC-VIGENTE",
    ]
    assert [documento["estado"] for documento in documentos] == ["VENCIDO", "VIGENTE"]
