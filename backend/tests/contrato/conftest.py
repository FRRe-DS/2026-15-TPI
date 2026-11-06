"""Fixtures de contrato (T098).

La suite levanta la aplicación real con los repositorios SQL sobre un PostgreSQL
efímero (misma imagen que el Compose y que la fixture de integración de T097),
firma tokens JWT con una clave RSA exclusiva de prueba y valida cada respuesta
contra ``docs/contract/openapi.yaml`` con openapi-core.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import jwt
import pytest
from alembic import command
from alembic.config import Config
from app.api import dependencias
from app.api.configuracion import Settings, obtener_configuracion
from app.api.main import crear_app
from app.api.seguridad import obtener_cliente_jwks
from app.infraestructura.db.sesion import crear_engine, crear_sessionmaker
from app.infraestructura.repositorios.sql_unidad_de_trabajo import SqlUnidadDeTrabajo
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from openapi_core import OpenAPI
from openapi_core.testing import MockRequest, MockResponse
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.community.postgres import PostgresContainer

RAIZ_DEL_REPOSITORIO = Path(__file__).resolve().parents[3]
CONTRATO = RAIZ_DEL_REPOSITORIO / "docs" / "contract" / "openapi.yaml"
ALEMBIC_INI = RAIZ_DEL_REPOSITORIO / "infra" / "migraciones" / "alembic.ini"

IMAGEN_POSTGRES = "postgres:17.11-alpine"
USUARIO_DE_PRUEBA = "m3_test"
CLAVE_DE_PRUEBA = "test-clave-no-real"
BASE_DE_PRUEBA = "m3_test"

TABLAS_DE_M3 = (
    "conductor",
    "vehiculo",
    "vehiculo_tipo_servicio",
    "documento_conductor",
    "habilitacion_evento_conductor",
    "habilitacion_evento_vehiculo",
)

# Servidor declarado en el contrato. Se usa como host de las peticiones simuladas
# para que openapi-core resuelva el `servers` de la especificación.
URL_DEL_CONTRATO = "http://localhost:8080"
REALM = "m3"
EMISOR = f"{URL_DEL_CONTRATO}/realms/{REALM}"
KID_PRUEBA = "contrato-key-1"
DATABASE_URL_DE_PRUEBA = "postgresql+psycopg://test:test@localhost:5432/test"


def _docker_disponible() -> bool:
    try:
        import docker

        return bool(docker.from_env(timeout=2).ping())
    except Exception:
        return False


def _migrar_a_head(url: str) -> None:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")


def _vaciar_tablas(engine: Engine) -> None:
    with engine.begin() as conexion:
        conexion.execute(text(f"TRUNCATE {', '.join(TABLAS_DE_M3)} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="session")
def url_contrato() -> Iterator[str]:
    """URL de una base PostgreSQL efímera con el esquema migrado a head."""
    if not _docker_disponible():
        pytest.skip("Docker no esta disponible: se omiten las pruebas de contrato con la API real.")
    contenedor = PostgresContainer(
        IMAGEN_POSTGRES,
        username=USUARIO_DE_PRUEBA,
        password=CLAVE_DE_PRUEBA,
        dbname=BASE_DE_PRUEBA,
        driver="psycopg",
    )
    with contenedor:
        url = contenedor.get_connection_url()
        _migrar_a_head(url)
        yield url


@pytest.fixture(scope="session")
def engine_contrato(url_contrato: str) -> Iterator[Engine]:
    engine = crear_engine(url_contrato)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def fabrica_sesiones_contrato(engine_contrato: Engine) -> sessionmaker[Session]:
    return crear_sessionmaker(engine_contrato)


@pytest.fixture(scope="session")
def clave_rsa() -> rsa.RSAPrivateKey:
    """Genera una clave RSA exclusiva para los tokens de prueba."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


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
    """Crea un JWT firmado con la clave de prueba, con emisor y expiración válidos."""

    def _crear_token(
        roles: list[str] | None = None,
        id_operador: Any = None,
        exp: datetime | int | None = None,
        iss: str = EMISOR,
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


@pytest.fixture(scope="session")
def configuracion_contrato() -> Settings:
    return Settings(
        KEYCLOAK_URL=URL_DEL_CONTRATO,
        KEYCLOAK_REALM=REALM,
        DATABASE_URL=DATABASE_URL_DE_PRUEBA,
    )


@pytest.fixture
def app_contrato(
    fabrica_sesiones_contrato: sessionmaker[Session],
    cliente_jwks: SimpleNamespace,
    configuracion_contrato: Settings,
) -> Iterator[FastAPI]:
    """Aplicación real con repositorios SQL y autenticación de prueba."""
    app = crear_app()

    def obtener_unidad_de_trabajo() -> Iterator[SqlUnidadDeTrabajo]:
        yield SqlUnidadDeTrabajo(fabrica_sesiones_contrato)

    app.dependency_overrides[dependencias.obtener_unidad_de_trabajo] = obtener_unidad_de_trabajo
    app.dependency_overrides[obtener_cliente_jwks] = lambda: cliente_jwks
    app.dependency_overrides[obtener_configuracion] = lambda: configuracion_contrato
    try:
        yield app
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def cliente(
    app_contrato: FastAPI,
    engine_contrato: Engine,
) -> Iterator[TestClient]:
    """Cliente HTTP contra la aplicación real, con la base vacía antes y después."""
    _vaciar_tablas(engine_contrato)
    try:
        with TestClient(app_contrato) as test_client:
            yield test_client
    finally:
        _vaciar_tablas(engine_contrato)


CONDUCTOR_DE_PRUEBA = {
    "dni": "30123456",
    "nombre": "Ana",
    "apellido": "Gómez",
    "telefono": "+5491176543210",
    "email": "ana.gomez@example.com",
}

FECHA_ACTUAL_DE_PRUEBA = datetime.now(UTC).date()
FECHA_EMISION_LICENCIA_VIGENTE = FECHA_ACTUAL_DE_PRUEBA - timedelta(days=365)
FECHA_VENCIMIENTO_LICENCIA_VIGENTE = FECHA_ACTUAL_DE_PRUEBA + timedelta(days=3 * 365)

LICENCIA_DE_PRUEBA = {
    "tipo": "LICENCIA",
    "numero": "LIC-12345678",
    "categoria": "B1",
    "fecha_emision": FECHA_EMISION_LICENCIA_VIGENTE.isoformat(),
    "fecha_vencimiento": FECHA_VENCIMIENTO_LICENCIA_VIGENTE.isoformat(),
    "url_archivo": "https://storage.example.com/licencias/1.pdf",
}

VEHICULO_DE_PRUEBA = {
    "tipo": "AUTO",
    "patente": "AB123CD",
    "marca": "Toyota",
    "modelo": "Corolla",
    "anio": 2022,
    "tipos_serv": ["PASAJEROS"],
}


@pytest.fixture
def crear_conductor(cliente: TestClient, headers_conductor: dict[str, str]):
    """Crea un conductor por la API y devuelve su representación."""

    def _crear_conductor(**cambios: str) -> dict[str, Any]:
        datos = {**CONDUCTOR_DE_PRUEBA, **cambios}
        respuesta = cliente.post("/api/v1/conductores", json=datos, headers=headers_conductor)
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    return _crear_conductor


@pytest.fixture
def registrar_licencia(cliente: TestClient, headers_conductor: dict[str, str]):
    """Registra una licencia por la API y devuelve la respuesta HTTP."""

    def _registrar_licencia(id_conductor: int, **cambios: Any) -> httpx.Response:
        datos = {**LICENCIA_DE_PRUEBA, **cambios}
        return cliente.post(
            f"/api/v1/conductores/{id_conductor}/documentacion",
            json=datos,
            headers=headers_conductor,
        )

    return _registrar_licencia


@pytest.fixture
def crear_vehiculo(cliente: TestClient, headers_conductor: dict[str, str]):
    """Registra un vehículo por la API y devuelve la respuesta HTTP."""

    def _crear_vehiculo(id_conductor: int, **cambios: Any) -> httpx.Response:
        datos = {**VEHICULO_DE_PRUEBA, **cambios}
        return cliente.post(
            f"/api/v1/conductores/{id_conductor}/vehiculos",
            json=datos,
            headers=headers_conductor,
        )

    return _crear_vehiculo


@pytest.fixture(scope="session")
def especificacion() -> OpenAPI:
    assert CONTRATO.exists(), f"No se encontro el contrato en {CONTRATO}"
    return OpenAPI.from_file_path(str(CONTRATO))


def _peticion_de(respuesta: httpx.Response) -> MockRequest:
    peticion = respuesta.request
    return MockRequest(
        host_url=URL_DEL_CONTRATO,
        method=peticion.method,
        path=peticion.url.path,
        args=dict(peticion.url.params),
        headers=dict(peticion.headers),
        data=peticion.content,
        content_type=peticion.headers.get("content-type", "application/json"),
    )


def _respuesta_de(respuesta: httpx.Response) -> MockResponse:
    return MockResponse(
        data=respuesta.content,
        status_code=respuesta.status_code,
        headers=dict(respuesta.headers),
        content_type=respuesta.headers.get("content-type", ""),
    )


@pytest.fixture
def validar_contrato(especificacion: OpenAPI):
    """Valida la petición y la respuesta contra el contrato OpenAPI."""

    def _validar(respuesta: httpx.Response) -> None:
        peticion = _peticion_de(respuesta)
        especificacion.validate_request(peticion)
        especificacion.validate_response(peticion, _respuesta_de(respuesta))

    return _validar


@pytest.fixture
def validar_respuesta(especificacion: OpenAPI):
    """Valida solo la respuesta contra el contrato OpenAPI.

    Se usa cuando la petición no puede validarse por diseño, por ejemplo un
    ``401`` sin encabezado ``Authorization``.
    """

    def _validar(respuesta: httpx.Response) -> None:
        peticion = _peticion_de(respuesta)
        especificacion.validate_response(peticion, _respuesta_de(respuesta))

    return _validar
