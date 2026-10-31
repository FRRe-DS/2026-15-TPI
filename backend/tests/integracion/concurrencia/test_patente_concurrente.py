"""T105: 20 solicitudes simultaneas con la misma patente."""

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

VEHICULO = {
    "tipo": "AUTO",
    "patente": "AB123CD",
    "marca": "Toyota",
    "modelo": "Corolla",
    "anio": 2022,
    "tipos_serv": ["PASAJEROS"],
}


def _crear_conductor(cliente: TestClient, headers: dict[str, str]) -> int:
    respuesta = cliente.post("/api/v1/conductores", json=CONDUCTOR, headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return int(respuesta.json()["id"])


def _crear_vehiculo(
    cliente: TestClient,
    headers: dict[str, str],
    id_conductor: int,
) -> httpx.Response:
    return cliente.post(
        f"/api/v1/conductores/{id_conductor}/vehiculos",
        json=VEHICULO,
        headers=headers,
    )


def test_veinte_solicitudes_simultaneas_con_la_misma_patente_dan_un_201_y_diecinueve_409(
    cliente: TestClient,
    headers_conductor: dict[str, str],
    peticiones_simultaneas: Callable[[Callable[[], httpx.Response]], list[httpx.Response]],
    sesion_bd: Session,
) -> None:
    id_conductor = _crear_conductor(cliente, headers_conductor)

    respuestas = peticiones_simultaneas(
        lambda: _crear_vehiculo(cliente, headers_conductor, id_conductor)
    )

    estados = Counter(respuesta.status_code for respuesta in respuestas)
    assert estados == Counter({201: 1, 409: 19})

    exitosas = [respuesta for respuesta in respuestas if respuesta.status_code == 201]
    conflictos = [respuesta for respuesta in respuestas if respuesta.status_code == 409]
    assert exitosas[0].json()["patente"] == VEHICULO["patente"]
    assert {respuesta.json()["codigo"] for respuesta in conflictos} == {"PATENTE_DUPLICADA"}

    total = sesion_bd.execute(
        text("SELECT count(*) FROM vehiculo WHERE patente = :patente"),
        {"patente": VEHICULO["patente"]},
    ).scalar_one()
    total_servicios = sesion_bd.execute(
        text("SELECT count(*) FROM vehiculo_tipo_servicio")
    ).scalar_one()
    assert total == 1
    assert total_servicios == 1
