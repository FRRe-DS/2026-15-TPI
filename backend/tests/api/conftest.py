from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from app.api import dependencias
from app.api.main import crear_app
from app.api.seguridad import obtener_cliente_jwks
from app.aplicacion.casos_de_uso.resultados import (
    ConductorDetalle,
    DocumentoDeConductor,
    HabilitacionEventos,
    HabilitacionResumen,
    HabilitacionVehiculoEventos,
    VehiculoDetalle,
)
from app.dominio.conductor import Conductor
from app.dominio.documento import Documento, EstadoDocumento, TipoDocumento
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.vehiculo import (
    ServicioDelVehiculo,
    TipoServicio,
    TipoVehiculo,
    Vehiculo,
)
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

EMISOR_VALIDO = "http://localhost:8080/realms/m3"
KID_PRUEBA = "test-key-1"

VARIABLES_ENTORNO = {
    "KEYCLOAK_URL": "http://localhost:8080",
    "KEYCLOAK_REALM": "m3",
    "DATABASE_URL": "postgresql+psycopg://test:test@localhost:5432/test",
}


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


def conductor_de_prueba(**cambios: Any) -> Conductor:
    datos: dict[str, Any] = {
        "dni": "12345678",
        "nombre": "Ana",
        "apellido": "Pérez",
        "telefono": "3415550000",
        "email": "ana@example.com",
        "habilitacion": EstadoHabilitacion.APROBADA,
        "conectado": True,
        "disponible": True,
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


@pytest.fixture(scope="session")
def clave_rsa() -> rsa.RSAPrivateKey:
    """Genera una clave RSA exclusiva para las pruebas."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def jwks(clave_rsa: rsa.RSAPrivateKey) -> dict[str, Any]:
    """Publica la clave pública en formato JWKS."""
    public_jwk = jwt.algorithms.RSAAlgorithm.to_jwk(
        clave_rsa.public_key(),
        as_dict=True,
    )
    public_jwk.update({"kid": KID_PRUEBA, "use": "sig", "alg": "RS256"})
    return {"keys": [public_jwk]}


@pytest.fixture(scope="session")
def cliente_jwks(clave_rsa: rsa.RSAPrivateKey) -> SimpleNamespace:
    """Cliente JWKS falso que entrega la clave pública de prueba."""

    def get_signing_key_from_jwt(token: str) -> SimpleNamespace:
        encabezado = jwt.get_unverified_header(token)
        if encabezado.get("kid") != KID_PRUEBA:
            raise jwt.exceptions.PyJWKClientError("Clave de prueba desconocida")
        return SimpleNamespace(key=clave_rsa.public_key())

    return SimpleNamespace(get_signing_key_from_jwt=get_signing_key_from_jwt)


@pytest.fixture
def crear_token(clave_rsa: rsa.RSAPrivateKey):
    """Crea un JWT firmado con la clave de prueba."""

    def _crear_token(
        roles: list[str] | None = None,
        id_operador: Any = None,
        exp: datetime | int | None = None,
        iss: str = EMISOR_VALIDO,
        kid: str = KID_PRUEBA,
    ) -> str:
        ahora = datetime.now(UTC)
        expiracion = exp if exp is not None else ahora + timedelta(minutes=15)
        payload: dict[str, Any] = {
            "iss": iss,
            "iat": int(ahora.timestamp()),
            "exp": expiracion,
            "realm_access": {
                "roles": roles if roles is not None else ["conductor"],
            },
        }
        if id_operador is not None:
            payload["id_operador"] = id_operador
        return jwt.encode(
            payload,
            clave_rsa,
            algorithm="RS256",
            headers={"kid": kid},
        )

    return _crear_token


@pytest.fixture
def headers_conductor(crear_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token(roles=['conductor'])}"}


@pytest.fixture
def headers_operador(crear_token) -> dict[str, str]:
    token = crear_token(roles=["operador"], id_operador=7)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable, valor in VARIABLES_ENTORNO.items():
        monkeypatch.setenv(variable, valor)


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


def _devolver(caso: CasoDeUsoFalso):
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
    for nombre, proveedor in PROVEEDORES:
        # Sin argumentos: FastAPI copia los valores por defecto de los
        # parámetros y devolvería una copia del caso de uso.
        app.dependency_overrides[proveedor] = _devolver(casos[nombre])
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
