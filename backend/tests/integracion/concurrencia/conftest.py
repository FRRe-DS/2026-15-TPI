"""Fixtures de las pruebas de concurrencia (T104-T105).

La aplicacion real corre con los repositorios SQL sobre la base PostgreSQL
efimera de `tests/integracion/conftest.py`. Los JWT se firman con una clave RSA
exclusiva de prueba y se publican mediante un cliente JWKS falso, igual que en
las pruebas de contrato.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from types import SimpleNamespace
from typing import Any

import httpx
import jwt
import pytest
from app.api import dependencias
from app.api.configuracion import Settings, obtener_configuracion
from app.api.main import crear_app
from app.api.seguridad import obtener_cliente_jwks
from app.infraestructura.repositorios.sql_unidad_de_trabajo import SqlUnidadDeTrabajo
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from tests.api.conftest import instalar_limitador_falso

URL_DE_PRUEBA = "http://localhost:8080"
REALM = "m3"
EMISOR = f"{URL_DE_PRUEBA}/realms/{REALM}"
KID_PRUEBA = "concurrencia-key-1"
DATABASE_URL_DE_PRUEBA = "postgresql+psycopg://test:test@localhost:5432/test"
CANTIDAD_DE_SOLICITUDES = 20
ESPERA_MAXIMA_DE_LA_BARRERA = 10
ESPERA_MAXIMA_DE_LAS_RESPUESTAS = 30


@pytest.fixture(scope="session")
def clave_rsa() -> rsa.RSAPrivateKey:
    """Genera una clave RSA exclusiva para los tokens de prueba."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def cliente_jwks(clave_rsa: rsa.RSAPrivateKey) -> SimpleNamespace:
    """Cliente JWKS falso que entrega la clave publica de prueba."""

    def get_signing_key_from_jwt(token: str) -> SimpleNamespace:
        encabezado = jwt.get_unverified_header(token)
        if encabezado.get("kid") != KID_PRUEBA:
            raise jwt.exceptions.PyJWKClientError("Clave de prueba desconocida")
        return SimpleNamespace(key=clave_rsa.public_key())

    return SimpleNamespace(get_signing_key_from_jwt=get_signing_key_from_jwt)


@pytest.fixture
def crear_token(clave_rsa: rsa.RSAPrivateKey):
    """Crea un JWT firmado con la clave de prueba, con emisor y expiracion validos."""

    def _crear_token(roles: list[str] | None = None, id_operador: Any = None) -> str:
        ahora = datetime.now(UTC)
        payload: dict[str, Any] = {
            "iss": EMISOR,
            "sub": "usuario-concurrencia",
            "iat": int(ahora.timestamp()),
            "exp": ahora + timedelta(minutes=15),
            "realm_access": {
                "roles": roles if roles is not None else ["conductor"],
            },
        }
        if id_operador is not None:
            payload["id_operador"] = id_operador
        return jwt.encode(payload, clave_rsa, algorithm="RS256", headers={"kid": KID_PRUEBA})

    return _crear_token


@pytest.fixture
def headers_conductor(crear_token) -> dict[str, str]:
    """Headers de quien opera sobre cualquier conductor (token de operador).

    Con la matriz de acceso de la Iteración 2 un token de conductor solo opera sobre su
    propio `id_conductor`, y estas pruebas operan sobre conductores recién creados, cuyo id
    se conoce recién después del alta. El nombre se conserva para no tocar las pruebas.
    """
    return {"Authorization": f"Bearer {crear_token(roles=['operador'], id_operador=7)}"}


@pytest.fixture
def headers_operador(crear_token) -> dict[str, str]:
    token = crear_token(roles=["operador"], id_operador=7)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def configuracion_concurrencia() -> Settings:
    return Settings(
        KEYCLOAK_URL=URL_DE_PRUEBA,
        KEYCLOAK_REALM=REALM,
        DATABASE_URL=DATABASE_URL_DE_PRUEBA,
        RATE_LIMIT_HMAC_SECRET="concurrency-test-hmac-secret-shared-by-instances",
    )


@pytest.fixture(scope="session")
def app_concurrencia(
    fabrica_sesiones: sessionmaker[Session],
    cliente_jwks: SimpleNamespace,
    configuracion_concurrencia: Settings,
) -> Iterator[FastAPI]:
    """Aplicacion real con repositorios SQL y autenticacion de prueba."""
    app = crear_app()
    app.state.settings = configuracion_concurrencia

    def obtener_unidad_de_trabajo() -> Iterator[SqlUnidadDeTrabajo]:
        yield SqlUnidadDeTrabajo(fabrica_sesiones)

    app.dependency_overrides[dependencias.obtener_unidad_de_trabajo] = obtener_unidad_de_trabajo
    app.dependency_overrides[obtener_cliente_jwks] = lambda: cliente_jwks
    app.dependency_overrides[obtener_configuracion] = lambda: configuracion_concurrencia
    instalar_limitador_falso(app)
    try:
        yield app
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def cliente(app_concurrencia: FastAPI) -> Iterator[TestClient]:
    with TestClient(app_concurrencia) as test_client:
        yield test_client


@pytest.fixture
def peticiones_simultaneas() -> Callable[..., list[httpx.Response]]:
    """Ejecuta peticiones que esperan juntas en una barrera antes de salir."""

    def _ejecutar(
        peticion: Callable[[], httpx.Response],
        cantidad: int = CANTIDAD_DE_SOLICITUDES,
    ) -> list[httpx.Response]:
        barrera = Barrier(cantidad)

        def _llamar() -> httpx.Response:
            barrera.wait(timeout=ESPERA_MAXIMA_DE_LA_BARRERA)
            return peticion()

        with ThreadPoolExecutor(max_workers=cantidad) as ejecutor:
            futuros = [ejecutor.submit(_llamar) for _ in range(cantidad)]
            return [futuro.result(timeout=ESPERA_MAXIMA_DE_LAS_RESPUESTAS) for futuro in futuros]

    return _ejecutar
