from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from app.api import dependencias
from app.api.main import crear_app
from app.api.seguridad import obtener_cliente_jwks, obtener_rate_limiter
from app.aplicacion.casos_de_uso.resultados import (
    ConductorDetalle,
    DocumentoDeConductor,
    HabilitacionEventos,
    HabilitacionResumen,
    HabilitacionVehiculoEventos,
    VehiculoDetalle,
)
from app.dominio.conductor import Conductor, EstadoConductor
from app.dominio.documento import Documento, EstadoDocumento, TipoDocumento
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.vehiculo import (
    ServicioDelVehiculo,
    TipoServicio,
    TipoVehiculo,
    Vehiculo,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient


class CasoDeUsoFalso:
    """Caso de uso simulado que registra sus llamadas y devuelve lo indicado."""

    def __init__(self, resultado: Any = None) -> None:
        self.resultado = resultado
        self.error: Exception | None = None
        self.llamadas: list[dict[str, Any]] = []

    def ejecutar(self, **kwargs: Any) -> Any:
        self.llamadas.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.resultado


class LimitadorSinCuota:
    def verificar(self, **_kwargs: Any) -> None:
        return None


def instalar_limitador_falso(app: FastAPI) -> None:
    app.dependency_overrides[obtener_rate_limiter] = LimitadorSinCuota


def conductor_de_prueba(**cambios: Any) -> Conductor:
    datos: dict[str, Any] = {
        "dni": "12345678",
        "nombre": "Ana",
        "apellido": "Pérez",
        "telefono": "3415550000",
        "email": "ana@example.com",
        "habilitacion": EstadoHabilitacion.APROBADA,
        "estado": EstadoConductor.DISPONIBLE,
        "id": 1,
    }
    datos.update(cambios)
    return Conductor(**datos)


def documento_de_prueba(**cambios: Any) -> Documento:
    datos: dict[str, Any] = {
        "tipo": TipoDocumento.LICENCIA,
        "numero": "LIC-1",
        "categoria": "B1",
        "fecha_emision": datetime(2020, 1, 1, tzinfo=UTC).date(),
        "fecha_vencimiento": datetime(2030, 1, 1, tzinfo=UTC).date(),
        "url_archivo": "https://archivos.example/licencia.pdf",
        "id": 10,
    }
    datos.update(cambios)
    return Documento(**datos)


def vehiculo_de_prueba(**cambios: Any) -> Vehiculo:
    datos: dict[str, Any] = {
        "tipo": TipoVehiculo.AUTO,
        "patente": "AB123CD",
        "marca": "Toyota",
        "modelo": "Corolla",
        "anio": 2020,
        "tipos_servicio": [ServicioDelVehiculo(TipoServicio.PASAJEROS)],
        "habilitacion": EstadoHabilitacion.APROBADA,
        "id": 5,
        "id_conductor": 1,
    }
    datos.update(cambios)
    return Vehiculo(**datos)


@pytest.fixture
def entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
    monkeypatch.setenv("KEYCLOAK_PUBLIC_URL", "http://localhost:8080")
    monkeypatch.setenv("KEYCLOAK_REALM", "m3")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
    monkeypatch.setenv(
        "RATE_LIMIT_HMAC_SECRET",
        "test-hmac-secret-shared-by-all-api-tests",
    )
    monkeypatch.setenv("RATE_LIMIT_ANON_REQUESTS", "60")
    monkeypatch.setenv("RATE_LIMIT_PREAUTH_REQUESTS", "1000")
    monkeypatch.setenv("RATE_LIMIT_AUTH_REQUESTS", "120")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")


@pytest.fixture
def casos() -> dict[str, CasoDeUsoFalso]:
    """Casos de uso simulados con resultados válidos por defecto."""
    conductor = conductor_de_prueba()
    detalle = ConductorDetalle(conductor=conductor, documentos=[], vehiculos=[])
    documento = documento_de_prueba()
    vehiculo = vehiculo_de_prueba()
    return {
        "crear_conductor": CasoDeUsoFalso(detalle),
        "listar_conductores": CasoDeUsoFalso([detalle]),
        "obtener_conductor": CasoDeUsoFalso(detalle),
        "consultar_habilitacion_conductor": CasoDeUsoFalso(
            HabilitacionResumen(
                id_conductor=1,
                estado=EstadoHabilitacion.APROBADA,
                historial=[],
            )
        ),
        "accionar_habilitacion_conductor": CasoDeUsoFalso(
            HabilitacionEventos(
                id_conductor=1,
                estado=EstadoHabilitacion.APROBADA,
                eventos=[],
            )
        ),
        "registrar_licencia": CasoDeUsoFalso(
            DocumentoDeConductor(
                id_conductor=1,
                documento=documento,
                estado=EstadoDocumento.VIGENTE,
            )
        ),
        "registrar_vehiculo": CasoDeUsoFalso(VehiculoDetalle(vehiculo=vehiculo)),
        "listar_vehiculos": CasoDeUsoFalso([vehiculo]),
        "obtener_vehiculo": CasoDeUsoFalso(VehiculoDetalle(vehiculo=vehiculo)),
        "accionar_habilitacion_vehiculo": CasoDeUsoFalso(
            HabilitacionVehiculoEventos(
                id_vehiculo=5,
                estado=EstadoHabilitacion.APROBADA,
                eventos=[],
            )
        ),
    }


PROVEEDORES = (
    ("crear_conductor", dependencias.obtener_caso_crear_conductor),
    ("listar_conductores", dependencias.obtener_caso_listar_conductores),
    ("obtener_conductor", dependencias.obtener_caso_obtener_conductor),
    (
        "consultar_habilitacion_conductor",
        dependencias.obtener_caso_consultar_habilitacion_conductor,
    ),
    (
        "accionar_habilitacion_conductor",
        dependencias.obtener_caso_accionar_habilitacion_conductor,
    ),
    ("registrar_licencia", dependencias.obtener_caso_registrar_licencia),
    ("registrar_vehiculo", dependencias.obtener_caso_registrar_vehiculo),
    ("listar_vehiculos", dependencias.obtener_caso_listar_vehiculos),
    ("obtener_vehiculo", dependencias.obtener_caso_obtener_vehiculo),
    (
        "accionar_habilitacion_vehiculo",
        dependencias.obtener_caso_accionar_habilitacion_vehiculo,
    ),
)


def devolver_caso(caso: CasoDeUsoFalso):
    """Crea un proveedor sin parámetros que siempre devuelve el mismo caso."""

    def proveedor() -> CasoDeUsoFalso:
        return caso

    return proveedor


@pytest.fixture
def client(
    casos: dict[str, CasoDeUsoFalso],
    cliente_jwks: SimpleNamespace,
    entorno: None,
) -> TestClient:
    """Cliente HTTP con JWT de prueba y casos de uso simulados."""
    app = crear_app()
    app.dependency_overrides[obtener_cliente_jwks] = lambda: cliente_jwks
    instalar_limitador_falso(app)
    for nombre, proveedor in PROVEEDORES:
        # Sin argumentos: FastAPI copia los valores por defecto de los
        # parámetros y devolvería una copia del caso de uso.
        app.dependency_overrides[proveedor] = devolver_caso(casos[nombre])
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
