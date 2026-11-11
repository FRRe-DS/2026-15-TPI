"""T104: 20 solicitudes simultaneas con el mismo DNI (SC-005)."""

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


def _crear_conductor(
    cliente: TestClient,
    headers: dict[str, str],
) -> httpx.Response:
    return cliente.post("/api/v1/conductores", json=CONDUCTOR, headers=headers)


def test_veinte_solicitudes_simultaneas_con_el_mismo_dni_dan_un_201_y_diecinueve_409(
    cliente: TestClient,
    headers_conductor: dict[str, str],
    peticiones_simultaneas: Callable[..., list[httpx.Response]],
    sesion_bd: Session,
) -> None:
    respuestas = peticiones_simultaneas(lambda: _crear_conductor(cliente, headers_conductor))

    estados = Counter(respuesta.status_code for respuesta in respuestas)
    assert estados == Counter({201: 1, 409: 19})

    exitosas = [respuesta for respuesta in respuestas if respuesta.status_code == 201]
    conflictos = [respuesta for respuesta in respuestas if respuesta.status_code == 409]
    assert exitosas[0].json()["dni"] == CONDUCTOR["dni"]
    assert {respuesta.json()["codigo"] for respuesta in conflictos} == {"DNI_DUPLICADO"}

    total = sesion_bd.execute(
        text("SELECT count(*) FROM conductor WHERE dni = :dni"),
        {"dni": CONDUCTOR["dni"]},
    ).scalar_one()
    assert total == 1
