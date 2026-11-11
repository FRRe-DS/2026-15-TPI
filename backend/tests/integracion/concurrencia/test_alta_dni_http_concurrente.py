"""T603: dos altas HTTP concurrentes con el mismo DNI.

La prueba usa dos clientes HTTP independientes y una barrera de inicio para
que ambas solicitudes salgan juntas. No usa `sleep` para inducir la carrera:
la exclusion la resuelve PostgreSQL mediante la restriccion unica de DNI.
"""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

ESPERA_MAXIMA_DE_LA_BARRERA = 10
ESPERA_MAXIMA_DE_LAS_RESPUESTAS = 30


def _dni_unico() -> str:
    """Genera un DNI de 8 digitos propio de esta ejecucion."""
    return str(10_000_000 + uuid4().int % 90_000_000)


def _datos_del_conductor(dni: str) -> dict[str, str]:
    return {
        "dni": dni,
        "nombre": "Ana",
        "apellido": "Gomez",
        "telefono": "+5491176543210",
        "email": f"concurrente-{dni}@example.com",
    }


def _crear_conductor(
    cliente: TestClient,
    headers: dict[str, str],
    datos: dict[str, str],
) -> httpx.Response:
    return cliente.post("/api/v1/conductores", json=datos, headers=headers)


def _dos_altas_simultaneas(
    primer_cliente: TestClient,
    segundo_cliente: TestClient,
    headers: dict[str, str],
    datos: dict[str, str],
) -> list[httpx.Response]:
    """Dispara dos POST con clientes distintos y una unica barrera de inicio."""
    barrera = Barrier(2)

    def _enviar(cliente: TestClient) -> httpx.Response:
        barrera.wait(timeout=ESPERA_MAXIMA_DE_LA_BARRERA)
        return _crear_conductor(cliente, headers, datos)

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        futuros = [
            ejecutor.submit(_enviar, primer_cliente),
            ejecutor.submit(_enviar, segundo_cliente),
        ]
        return [futuro.result(timeout=ESPERA_MAXIMA_DE_LAS_RESPUESTAS) for futuro in futuros]


def test_dos_altas_http_simultaneas_con_el_mismo_dni_dejan_un_solo_conductor_y_evento(
    clientes_independientes: tuple[TestClient, TestClient],
    headers_operador: dict[str, str],
    sesion_bd: Session,
) -> None:
    dni = _dni_unico()
    datos = _datos_del_conductor(dni)
    primer_cliente, segundo_cliente = clientes_independientes

    respuestas = _dos_altas_simultaneas(
        primer_cliente,
        segundo_cliente,
        headers_operador,
        datos,
    )

    estados = Counter(respuesta.status_code for respuesta in respuestas)
    assert estados == Counter({201: 1, 409: 1})

    exitosas = [respuesta for respuesta in respuestas if respuesta.status_code == 201]
    conflictos = [respuesta for respuesta in respuestas if respuesta.status_code == 409]
    assert exitosas[0].json()["dni"] == dni
    assert conflictos[0].json()["codigo"] == "DNI_DUPLICADO"

    filas = sesion_bd.execute(
        text(
            """
            SELECT id_conductor
            FROM conductor
            WHERE dni = :dni
            """
        ),
        {"dni": dni},
    ).all()
    assert len(filas) == 1

    id_conductor = filas[0].id_conductor
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
    assert [tuple(evento) for evento in eventos] == [("ALTA", None, "PENDIENTE")]
