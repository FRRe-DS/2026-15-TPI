"""Flujo HTTP de estado y ubicación respaldado por PostgreSQL y el seed de M3."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from app.api import dependencias
from app.api.main import crear_app
from app.api.seguridad import obtener_cliente_jwks
from app.infraestructura.db.modelos import Conductor, Vehiculo
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from tests.api.conftest import instalar_limitador_falso

URL_ESTADO = "/api/v1/conductores/{id_conductor}/estado"
URL_UBICACION = "/api/v1/conductores/{id_conductor}/ubicacion"
LATITUD_SIMULADA = -27.4511
LONGITUD_SIMULADA = -58.9867

RUTA_SEED = Path(__file__).resolve().parents[4] / "infra" / "seed" / "cargar_datos.py"
ESPECIFICACION_SEED = importlib.util.spec_from_file_location("seed_m3_integracion", RUTA_SEED)
if ESPECIFICACION_SEED is None or ESPECIFICACION_SEED.loader is None:
    raise RuntimeError(f"No se pudo cargar el seed de M3 desde {RUTA_SEED}")
MODULO_SEED = importlib.util.module_from_spec(ESPECIFICACION_SEED)
ESPECIFICACION_SEED.loader.exec_module(MODULO_SEED)
if not isinstance(MODULO_SEED, ModuleType):
    raise RuntimeError("El modulo del seed de M3 no se cargo correctamente")


@pytest.fixture
def cliente_estado(
    monkeypatch: pytest.MonkeyPatch,
    fabrica_sesiones: sessionmaker[Session],
    cliente_jwks,
    entorno: None,
) -> TestClient:
    monkeypatch.setenv("KEYCLOAK_PUBLIC_URL", "http://localhost:8080")
    monkeypatch.setenv("UBICACION_SIMULADA_LATITUD", str(LATITUD_SIMULADA))
    monkeypatch.setenv("UBICACION_SIMULADA_LONGITUD", str(LONGITUD_SIMULADA))
    monkeypatch.setattr(dependencias, "_fabrica_de_sesiones", lambda: fabrica_sesiones)
    app = crear_app()
    app.dependency_overrides[obtener_cliente_jwks] = lambda: cliente_jwks
    instalar_limitador_falso(app)
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


@pytest.fixture
def seed_estado(url_integracion: str, sesion_bd: Session) -> None:
    MODULO_SEED.cargar_datos(url_integracion)


def _conductor(sesion_bd: Session, dni: str) -> Conductor:
    conductor = sesion_bd.scalar(select(Conductor).where(Conductor.dni == dni))
    assert conductor is not None
    return conductor


def _vehiculo(sesion_bd: Session, patente: str) -> Vehiculo:
    vehiculo = sesion_bd.scalar(select(Vehiculo).where(Vehiculo.patente == patente))
    assert vehiculo is not None
    return vehiculo


def test_pedir_disponible_sin_aprobacion_responde_422(
    cliente_estado: TestClient,
    sesion_bd: Session,
    seed_estado: None,
    headers_conductor_de,
) -> None:
    conductor = _conductor(sesion_bd, "35777888")
    vehiculo = _vehiculo(sesion_bd, "AC456EF")
    vehiculo.estado_habilitacion = "APROBADA"
    conductor.id_vehiculo_activo = vehiculo.id_vehiculo
    sesion_bd.commit()

    respuesta = cliente_estado.patch(
        URL_ESTADO.format(id_conductor=conductor.id_conductor),
        json={"estado": "DISPONIBLE"},
        headers=headers_conductor_de(conductor.id_conductor),
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "CONDUCTOR_NO_HABILITADO"


def test_pedir_disponible_sin_vehiculo_activo_aprobado_responde_422(
    cliente_estado: TestClient,
    sesion_bd: Session,
    seed_estado: None,
    headers_conductor_de,
) -> None:
    conductor = _conductor(sesion_bd, "30111222")
    conductor.id_vehiculo_activo = None
    sesion_bd.commit()

    respuesta = cliente_estado.patch(
        URL_ESTADO.format(id_conductor=conductor.id_conductor),
        json={"estado": "DISPONIBLE"},
        headers=headers_conductor_de(conductor.id_conductor),
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "CONDUCTOR_NO_HABILITADO"


def test_desconectado_pasa_a_disponible_con_conductor_y_vehiculo_aprobados(
    cliente_estado: TestClient,
    sesion_bd: Session,
    seed_estado: None,
    headers_conductor_de,
) -> None:
    conductor = _conductor(sesion_bd, "30111222")
    conductor.estado = "DESCONECTADO"
    sesion_bd.commit()

    respuesta = cliente_estado.patch(
        URL_ESTADO.format(id_conductor=conductor.id_conductor),
        json={"estado": "DISPONIBLE"},
        headers=headers_conductor_de(conductor.id_conductor),
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "DISPONIBLE"
    persistido = cliente_estado.get(
        URL_ESTADO.format(id_conductor=conductor.id_conductor),
        headers=headers_conductor_de(conductor.id_conductor),
    )
    assert persistido.status_code == 200
    assert persistido.json()["estado"] == "DISPONIBLE"


def test_no_se_puede_pedir_ocupado_y_responde_400(
    cliente_estado: TestClient,
    sesion_bd: Session,
    seed_estado: None,
    headers_conductor_de,
) -> None:
    conductor = _conductor(sesion_bd, "40123456")

    respuesta = cliente_estado.patch(
        URL_ESTADO.format(id_conductor=conductor.id_conductor),
        json={"estado": "OCUPADO"},
        headers=headers_conductor_de(conductor.id_conductor),
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"


@pytest.mark.parametrize(
    ("cambiar_vehiculo", "patente"),
    [(False, None), (True, "TEST613")],
    ids=["quitar-vehiculo", "cambiar-vehiculo"],
)
def test_quitar_o_cambiar_vehiculo_activo_deja_conectado(
    cliente_estado: TestClient,
    sesion_bd: Session,
    seed_estado: None,
    headers_conductor_de,
    cambiar_vehiculo: bool,
    patente: str | None,
) -> None:
    conductor = _conductor(sesion_bd, "28444555")
    if cambiar_vehiculo:
        vehiculo_nuevo = Vehiculo(
            id_conductor=conductor.id_conductor,
            patente=patente,
            marca="Honda",
            modelo="CB 300",
            anio=2024,
            tipo="MOTO",
            estado_habilitacion="PENDIENTE",
        )
        sesion_bd.add(vehiculo_nuevo)
        sesion_bd.flush()
        cuerpo = {"id_vehiculo_activo": vehiculo_nuevo.id_vehiculo}
    else:
        cuerpo = {"id_vehiculo_activo": None}
    sesion_bd.commit()

    respuesta = cliente_estado.patch(
        URL_ESTADO.format(id_conductor=conductor.id_conductor),
        json=cuerpo,
        headers=headers_conductor_de(conductor.id_conductor),
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "CONECTADO"
    estado_persistido = cliente_estado.get(
        URL_ESTADO.format(id_conductor=conductor.id_conductor),
        headers=headers_conductor_de(conductor.id_conductor),
    )
    assert estado_persistido.status_code == 200
    assert estado_persistido.json()["estado"] == "CONECTADO"
    assert estado_persistido.json()["id_vehiculo_activo"] == cuerpo["id_vehiculo_activo"]


def test_get_ubicacion_sin_datos_devuelve_nulos_y_no_cero_cero(
    cliente_estado: TestClient,
    sesion_bd: Session,
    seed_estado: None,
    headers_servicio,
) -> None:
    conductor = _conductor(sesion_bd, "35777888")

    respuesta = cliente_estado.get(
        URL_UBICACION.format(id_conductor=conductor.id_conductor),
        headers=headers_servicio,
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id_conductor": conductor.id_conductor,
        "latitud": None,
        "longitud": None,
        "fecha_act_ubic": None,
    }
    assert (respuesta.json()["latitud"], respuesta.json()["longitud"]) != (0, 0)


def test_salir_de_desconectado_sin_ubicacion_asigna_ubicacion_simulada(
    cliente_estado: TestClient,
    sesion_bd: Session,
    seed_estado: None,
    headers_conductor_de,
    headers_servicio,
) -> None:
    conductor = _conductor(sesion_bd, "35777888")
    assert conductor.latitud is None
    assert conductor.longitud is None
    id_conductor = conductor.id_conductor

    respuesta = cliente_estado.patch(
        URL_ESTADO.format(id_conductor=id_conductor),
        json={"estado": "CONECTADO"},
        headers=headers_conductor_de(id_conductor),
    )
    ubicacion = cliente_estado.get(
        URL_UBICACION.format(id_conductor=id_conductor),
        headers=headers_servicio,
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "CONECTADO"
    assert ubicacion.status_code == 200
    assert ubicacion.json()["latitud"] == LATITUD_SIMULADA
    assert ubicacion.json()["longitud"] == LONGITUD_SIMULADA
    assert ubicacion.json()["fecha_act_ubic"] is not None
    assert (ubicacion.json()["latitud"], ubicacion.json()["longitud"]) != (0, 0)
