"""Carreras HTTP entre respuestas de solicitudes y cambios de estado."""

from __future__ import annotations

import importlib.util
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import ModuleType

import httpx
import pytest
from app.infraestructura.db.modelos import Conductor
from app.infraestructura.db.modelos import Solicitud as SolicitudDB
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

URL_ESTADO = "/api/v1/conductores/{id_conductor}/estado"
URL_UBICACION = "/api/v1/conductores/{id_conductor}/ubicacion"
URL_RESPONDER = "/api/v1/solicitudes/{id_solicitud}"
HORA_RESPUESTA = "2026-11-10T12:00:00Z"
COORDENADAS = {"latitud": -33.4489, "longitud": -70.6693}
RUTA_SEED = Path(__file__).resolve().parents[4] / "infra" / "seed" / "cargar_datos.py"
ESPECIFICACION_SEED = importlib.util.spec_from_file_location("seed_m3_concurrencia", RUTA_SEED)
if ESPECIFICACION_SEED is None or ESPECIFICACION_SEED.loader is None:
    raise RuntimeError(f"No se pudo cargar el seed de M3 desde {RUTA_SEED}")
MODULO_SEED = importlib.util.module_from_spec(ESPECIFICACION_SEED)
ESPECIFICACION_SEED.loader.exec_module(MODULO_SEED)
if not isinstance(MODULO_SEED, ModuleType):
    raise RuntimeError("El modulo del seed de M3 no se cargo correctamente")


@pytest.fixture
def seed_concurrencia(url_integracion: str) -> None:
    MODULO_SEED.cargar_datos(url_integracion)


def _conductor(sesion_bd: Session) -> Conductor:
    conductor = sesion_bd.scalar(select(Conductor).where(Conductor.dni == "30111222"))
    assert conductor is not None
    return conductor


def _solicitud_vigente(sesion_bd: Session) -> SolicitudDB:
    solicitud = sesion_bd.scalar(select(SolicitudDB).where(SolicitudDB.id_viaje == 1001))
    assert solicitud is not None
    return solicitud


def _ejecutar_en_paralelo(*peticiones):
    barrera = Barrier(len(peticiones))

    def llamar(peticion):
        barrera.wait(timeout=10)
        return peticion()

    with ThreadPoolExecutor(max_workers=len(peticiones)) as ejecutor:
        futuros = [ejecutor.submit(llamar, peticion) for peticion in peticiones]
        return [futuro.result(timeout=30) for futuro in futuros]


def test_doble_aceptacion_paralela_responde_una_vez_y_luego_409(
    clientes_independientes: tuple[TestClient, TestClient],
    headers_conductor_de,
    headers_servicio: dict[str, str],
    sesion_bd: Session,
    seed_concurrencia: None,
) -> None:
    conductor = _conductor(sesion_bd)
    solicitud = _solicitud_vigente(sesion_bd)
    id_conductor = conductor.id_conductor
    id_solicitud = solicitud.id_solicitud
    sesion_bd.commit()
    primer_cliente, segundo_cliente = clientes_independientes

    respuestas = _ejecutar_en_paralelo(
        lambda: _responder_con_headers(
            primer_cliente,
            id_solicitud,
            headers_conductor_de(id_conductor),
        ),
        lambda: _responder_con_headers(
            segundo_cliente,
            id_solicitud,
            headers_conductor_de(id_conductor),
        ),
    )

    estados = Counter(respuesta.status_code for respuesta in respuestas)
    assert estados == Counter({200: 1, 409: 1})
    conflicto = next(respuesta for respuesta in respuestas if respuesta.status_code == 409)
    assert conflicto.json()["codigo"] == "SOLICITUD_YA_RESPONDIDA"
    estado = primer_cliente.get(
        URL_ESTADO.format(id_conductor=conductor.id_conductor), headers=headers_servicio
    )
    assert estado.status_code == 200
    assert estado.json()["estado"] == "OCUPADO"


def _responder_con_headers(
    cliente: TestClient, id_solicitud: int, headers: dict[str, str]
) -> httpx.Response:
    return cliente.post(
        URL_RESPONDER.format(id_solicitud=id_solicitud),
        json={"respuesta": "ACEPTADO", "hora_rta": HORA_RESPUESTA},
        headers=headers,
    )


def test_patch_ubicacion_concurrente_con_aceptacion_conserva_ambos_cambios(
    clientes_independientes: tuple[TestClient, TestClient],
    headers_conductor_de,
    headers_servicio: dict[str, str],
    sesion_bd: Session,
    seed_concurrencia: None,
) -> None:
    conductor = _conductor(sesion_bd)
    solicitud = _solicitud_vigente(sesion_bd)
    id_conductor = conductor.id_conductor
    id_solicitud = solicitud.id_solicitud
    sesion_bd.commit()
    cliente_estado, cliente_solicitud = clientes_independientes

    respuestas = _ejecutar_en_paralelo(
        lambda: cliente_estado.patch(
            URL_ESTADO.format(id_conductor=id_conductor),
            json=COORDENADAS,
            headers=headers_conductor_de(id_conductor),
        ),
        lambda: _responder_con_headers(
            cliente_solicitud, id_solicitud, headers_conductor_de(id_conductor)
        ),
    )

    assert [respuesta.status_code for respuesta in respuestas] == [200, 200]
    estado = cliente_estado.get(
        URL_ESTADO.format(id_conductor=id_conductor), headers=headers_servicio
    )
    ubicacion = cliente_estado.get(
        URL_UBICACION.format(id_conductor=id_conductor), headers=headers_servicio
    )
    assert estado.status_code == 200
    assert estado.json()["estado"] == "OCUPADO"
    assert ubicacion.status_code == 200
    assert ubicacion.json()["latitud"] == COORDENADAS["latitud"]
    assert ubicacion.json()["longitud"] == COORDENADAS["longitud"]

    sesion_bd.expire_all()
    assert conductor.estado == "OCUPADO"
    assert conductor.latitud == COORDENADAS["latitud"]
    assert conductor.longitud == COORDENADAS["longitud"]
    assert solicitud.estado == "ACEPTADO"
