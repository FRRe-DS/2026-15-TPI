"""Flujo HTTP de solicitudes respaldado por PostgreSQL y el seed de M3."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType

import httpx
import pytest
from app.api import dependencias
from app.api.main import crear_app
from app.api.seguridad import obtener_cliente_jwks
from app.infraestructura.db.modelos import Conductor
from app.infraestructura.db.modelos import Solicitud as SolicitudDB
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

URL_RESPONDER = "/api/v1/solicitudes/{id_solicitud}"
URL_CONDUCTOR = "/api/v1/conductores/{id_conductor}"
URL_ESTADO = "/api/v1/conductores/{id_conductor}/estado"
URL_UBICACION = "/api/v1/conductores/{id_conductor}/ubicacion"
URL_SOLICITUDES = "/api/v1/conductores/{id_conductor}/solicitudes"
HORA_RESPUESTA = "2026-11-10T12:00:00Z"

RUTA_SEED = Path(__file__).resolve().parents[4] / "infra" / "seed" / "cargar_datos.py"
ESPECIFICACION_SEED = importlib.util.spec_from_file_location("seed_m3_solicitudes", RUTA_SEED)
if ESPECIFICACION_SEED is None or ESPECIFICACION_SEED.loader is None:
    raise RuntimeError(f"No se pudo cargar el seed de M3 desde {RUTA_SEED}")
MODULO_SEED = importlib.util.module_from_spec(ESPECIFICACION_SEED)
ESPECIFICACION_SEED.loader.exec_module(MODULO_SEED)
if not isinstance(MODULO_SEED, ModuleType):
    raise RuntimeError("El modulo del seed de M3 no se cargo correctamente")


@pytest.fixture
def cliente_solicitudes_pg(
    monkeypatch: pytest.MonkeyPatch,
    fabrica_sesiones: sessionmaker[Session],
    cliente_jwks,
    entorno: None,
) -> TestClient:
    monkeypatch.setenv("KEYCLOAK_PUBLIC_URL", "http://localhost:8080")
    monkeypatch.setattr(dependencias, "_fabrica_de_sesiones", lambda: fabrica_sesiones)
    app = crear_app()
    app.dependency_overrides[obtener_cliente_jwks] = lambda: cliente_jwks
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


@pytest.fixture
def seed_solicitudes_pg(url_integracion: str) -> None:
    MODULO_SEED.cargar_datos(url_integracion)


def _conductor(sesion_bd: Session, dni: str) -> Conductor:
    conductor = sesion_bd.scalar(select(Conductor).where(Conductor.dni == dni))
    assert conductor is not None
    return conductor


def _solicitud(sesion_bd: Session, id_viaje: int) -> SolicitudDB:
    solicitud = sesion_bd.scalar(select(SolicitudDB).where(SolicitudDB.id_viaje == id_viaje))
    assert solicitud is not None
    return solicitud


def _responder(
    cliente: TestClient,
    id_solicitud: int,
    respuesta: str,
    headers: dict[str, str],
) -> httpx.Response:
    return cliente.post(
        URL_RESPONDER.format(id_solicitud=id_solicitud),
        json={"respuesta": respuesta, "hora_rta": HORA_RESPUESTA},
        headers=headers,
    )


@pytest.mark.parametrize("estado_inicial", ["CONECTADO", "DISPONIBLE"])
def test_aceptar_solicitud_vigente_deja_ocupado(
    cliente_solicitudes_pg: TestClient,
    sesion_bd: Session,
    seed_solicitudes_pg: None,
    headers_conductor_de,
    headers_servicio,
    estado_inicial: str,
) -> None:
    conductor = _conductor(sesion_bd, "30111222")
    conductor.estado = estado_inicial
    solicitud = _solicitud(sesion_bd, 1001)
    sesion_bd.commit()

    respuesta = _responder(
        cliente_solicitudes_pg,
        solicitud.id_solicitud,
        "ACEPTADO",
        headers_conductor_de(conductor.id_conductor),
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "ACEPTADO"
    assert respuesta.json()["respuesta"] == "ACEPTADO"
    estado = cliente_solicitudes_pg.get(
        URL_ESTADO.format(id_conductor=conductor.id_conductor), headers=headers_servicio
    )
    assert estado.status_code == 200
    assert estado.json()["estado"] == "OCUPADO"
    solicitudes = cliente_solicitudes_pg.get(
        URL_SOLICITUDES.format(id_conductor=conductor.id_conductor),
        headers=headers_conductor_de(conductor.id_conductor),
    )
    assert solicitudes.status_code == 200
    assert (
        next(item for item in solicitudes.json() if item["id"] == solicitud.id_solicitud)["estado"]
        == "ACEPTADO"
    )


def test_rechazar_solicitud_vigente_persiste_rechazo_sin_ocupar(
    cliente_solicitudes_pg: TestClient,
    sesion_bd: Session,
    seed_solicitudes_pg: None,
    headers_conductor_de,
    headers_servicio,
) -> None:
    conductor = _conductor(sesion_bd, "30111222")
    solicitud = _solicitud(sesion_bd, 1001)
    sesion_bd.commit()

    respuesta = _responder(
        cliente_solicitudes_pg,
        solicitud.id_solicitud,
        "RECHAZADO",
        headers_conductor_de(conductor.id_conductor),
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "RECHAZADO"
    assert respuesta.json()["respuesta"] == "RECHAZADO"
    estado = cliente_solicitudes_pg.get(
        URL_ESTADO.format(id_conductor=conductor.id_conductor), headers=headers_servicio
    )
    assert estado.status_code == 200
    assert estado.json()["estado"] == "CONECTADO"
    solicitudes = cliente_solicitudes_pg.get(
        URL_SOLICITUDES.format(id_conductor=conductor.id_conductor),
        headers=headers_conductor_de(conductor.id_conductor),
    )
    assert solicitudes.status_code == 200
    assert (
        next(item for item in solicitudes.json() if item["id"] == solicitud.id_solicitud)["estado"]
        == "RECHAZADO"
    )


@pytest.mark.parametrize("estado_inicial", ["DESCONECTADO", "OCUPADO"])
def test_aceptar_solicitud_no_habilitada_responde_422(
    cliente_solicitudes_pg: TestClient,
    sesion_bd: Session,
    seed_solicitudes_pg: None,
    headers_conductor_de,
    estado_inicial: str,
) -> None:
    conductor = _conductor(sesion_bd, "30111222")
    conductor.estado = estado_inicial
    solicitud = _solicitud(sesion_bd, 1001)
    sesion_bd.commit()

    respuesta = _responder(
        cliente_solicitudes_pg,
        solicitud.id_solicitud,
        "ACEPTADO",
        headers_conductor_de(conductor.id_conductor),
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "CONDUCTOR_NO_HABILITADO"


def test_responder_solicitud_vencida_responde_410(
    cliente_solicitudes_pg: TestClient,
    sesion_bd: Session,
    seed_solicitudes_pg: None,
    headers_conductor_de,
) -> None:
    solicitud = _solicitud(sesion_bd, 1002)
    id_solicitud = solicitud.id_solicitud
    sesion_bd.commit()

    conductor = _conductor(sesion_bd, "30111222")
    respuesta = _responder(
        cliente_solicitudes_pg,
        id_solicitud,
        "ACEPTADO",
        headers_conductor_de(conductor.id_conductor),
    )

    assert respuesta.status_code == 410
    assert respuesta.json()["codigo"] == "SOLICITUD_VENCIDA"


def test_respuesta_duplicada_secuencial_responde_409(
    cliente_solicitudes_pg: TestClient,
    sesion_bd: Session,
    seed_solicitudes_pg: None,
    headers_conductor_de,
) -> None:
    solicitud = _solicitud(sesion_bd, 1001)
    id_solicitud = solicitud.id_solicitud
    sesion_bd.commit()

    conductor = _conductor(sesion_bd, "30111222")
    headers = headers_conductor_de(conductor.id_conductor)
    primera = _responder(cliente_solicitudes_pg, id_solicitud, "RECHAZADO", headers)
    segunda = _responder(cliente_solicitudes_pg, id_solicitud, "ACEPTADO", headers)

    assert primera.status_code == 200, primera.text
    assert segunda.status_code == 409
    assert segunda.json()["codigo"] == "SOLICITUD_YA_RESPONDIDA"


def test_endpoints_no_alteran_calificaciones_del_seed(
    cliente_solicitudes_pg: TestClient,
    sesion_bd: Session,
    seed_solicitudes_pg: None,
    headers_conductor_de,
    headers_servicio,
) -> None:
    conductor_sin_calificaciones = _conductor(sesion_bd, "28444555")
    conductor_calificado = _conductor(sesion_bd, "30111222")
    assert (
        conductor_sin_calificaciones.suma_puntajes,
        conductor_sin_calificaciones.cantidad_calificaciones,
    ) == (0, 0)
    assert (
        conductor_calificado.suma_puntajes,
        conductor_calificado.cantidad_calificaciones,
    ) == (20, 4)
    id_sin_calificaciones = conductor_sin_calificaciones.id_conductor
    id_calificado = conductor_calificado.id_conductor

    respuestas_get = (
        cliente_solicitudes_pg.get(
            URL_CONDUCTOR.format(id_conductor=id_sin_calificaciones),
            headers=headers_servicio,
        ),
        cliente_solicitudes_pg.get("/api/v1/conductores", headers=headers_servicio),
        cliente_solicitudes_pg.get(
            URL_ESTADO.format(id_conductor=id_sin_calificaciones),
            headers=headers_servicio,
        ),
        cliente_solicitudes_pg.get(
            URL_UBICACION.format(id_conductor=id_sin_calificaciones),
            headers=headers_servicio,
        ),
        cliente_solicitudes_pg.get(
            URL_SOLICITUDES.format(id_conductor=id_sin_calificaciones),
            headers=headers_conductor_de(id_sin_calificaciones),
        ),
        cliente_solicitudes_pg.get(
            URL_CONDUCTOR.format(id_conductor=id_calificado),
            headers=headers_servicio,
        ),
    )
    assert all(respuesta.status_code == 200 for respuesta in respuestas_get)
    detalle_sin_calificaciones = respuestas_get[0].json()
    detalle_calificado = respuestas_get[5].json()
    assert detalle_sin_calificaciones["puntaje_promedio"] is None
    assert detalle_sin_calificaciones["cantidad_calificaciones"] == 0
    assert detalle_calificado["puntaje_promedio"] == 5.0
    assert detalle_calificado["cantidad_calificaciones"] == 4
    listado = respuestas_get[1].json()
    sin_calificaciones_en_lista = next(
        item for item in listado if item["id"] == id_sin_calificaciones
    )
    assert sin_calificaciones_en_lista["puntaje_promedio"] is None
    assert sin_calificaciones_en_lista["cantidad_calificaciones"] == 0

    conductor_sin_calificaciones.estado = "DISPONIBLE"
    solicitud_nueva = SolicitudDB(
        id_conductor=id_sin_calificaciones,
        id_viaje=9614,
        estado="PENDIENTE",
        vence_en=datetime.now(UTC) + timedelta(hours=1),
    )
    sesion_bd.add(solicitud_nueva)
    sesion_bd.commit()
    cambio_estado = cliente_solicitudes_pg.patch(
        URL_ESTADO.format(id_conductor=id_sin_calificaciones),
        json={"estado": "CONECTADO"},
        headers=headers_conductor_de(id_sin_calificaciones),
    )
    rechazo = _responder(
        cliente_solicitudes_pg,
        solicitud_nueva.id_solicitud,
        "RECHAZADO",
        headers_conductor_de(id_sin_calificaciones),
    )
    assert cambio_estado.status_code == 200, cambio_estado.text
    assert rechazo.status_code == 200, rechazo.text

    sesion_bd.expire_all()
    assert (
        conductor_sin_calificaciones.suma_puntajes,
        conductor_sin_calificaciones.cantidad_calificaciones,
    ) == (0, 0)
    assert (
        conductor_calificado.suma_puntajes,
        conductor_calificado.cantidad_calificaciones,
    ) == (20, 4)
