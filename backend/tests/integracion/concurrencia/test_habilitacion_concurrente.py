"""T106: dos acciones simultaneas de habilitacion sobre el mismo conductor."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

CONDUCTOR = {
    "dni": "30123456",
    "nombre": "Ana",
    "apellido": "Gomez",
    "telefono": "+5491176543210",
    "email": "ana.gomez@example.com",
}

LICENCIA = {
    "tipo": "LICENCIA",
    "numero": "LIC-30123456",
    "categoria": "B1",
    "fecha_emision": "2024-01-01",
    "fecha_vencimiento": "2035-12-31",
    "url_archivo": "https://storage.example.com/licencias/30123456.pdf",
}

APROBAR = {
    "accion": "APROBAR",
    "motivo": "Documentacion completa y licencia vigente",
}


def _crear_conductor(cliente: TestClient, headers: dict[str, str]) -> int:
    respuesta = cliente.post("/api/v1/conductores", json=CONDUCTOR, headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return int(respuesta.json()["id"])


def _registrar_licencia(
    cliente: TestClient,
    headers: dict[str, str],
    id_conductor: int,
) -> httpx.Response:
    return cliente.post(
        f"/api/v1/conductores/{id_conductor}/documentacion",
        json=LICENCIA,
        headers=headers,
    )


def _aprobar(cliente: TestClient, headers: dict[str, str], id_conductor: int) -> httpx.Response:
    return cliente.post(
        f"/api/v1/conductores/{id_conductor}/habilitacion",
        json=APROBAR,
        headers=headers,
    )


def test_dos_acciones_simultaneas_sobre_el_mismo_conductor_dejan_un_solo_evento_nuevo(
    cliente: TestClient,
    headers_conductor: dict[str, str],
    headers_operador: dict[str, str],
    peticiones_simultaneas: Callable[..., list[httpx.Response]],
    sesion_bd: Session,
) -> None:
    id_conductor = _crear_conductor(cliente, headers_conductor)
    licencia = _registrar_licencia(cliente, headers_conductor, id_conductor)
    assert licencia.status_code == 201, licencia.text

    respuestas = peticiones_simultaneas(
        lambda: _aprobar(cliente, headers_operador, id_conductor),
        cantidad=2,
    )

    estados = Counter(respuesta.status_code for respuesta in respuestas)
    assert estados == Counter({200: 1, 409: 1})

    exitosas = [respuesta for respuesta in respuestas if respuesta.status_code == 200]
    conflictos = [respuesta for respuesta in respuestas if respuesta.status_code == 409]
    assert exitosas[0].json()["estado"] == "APROBADA"
    assert conflictos[0].json()["codigo"] == "TRANSICION_INVALIDA"

    eventos = sesion_bd.execute(
        text(
            """
            SELECT accion, estado_anterior, estado_nuevo
            FROM habilitacion_evento_conductor
            WHERE id_conductor = :id_conductor
            ORDER BY id_evento
            """
        ),
        {"id_conductor": id_conductor},
    ).all()
    assert [tuple(evento) for evento in eventos] == [
        ("ALTA", None, "PENDIENTE"),
        ("APROBAR", "PENDIENTE", "APROBADA"),
    ]

    estado = sesion_bd.execute(
        text("SELECT estado_habilitacion FROM conductor WHERE id_conductor = :id_conductor"),
        {"id_conductor": id_conductor},
    ).scalar_one()
    assert estado == "APROBADA"
