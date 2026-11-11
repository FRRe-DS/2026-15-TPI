"""Fixtures E2E (T601, T612): API y Keycloak reales levantados por Docker Compose.

No se firman tokens de prueba: cada token se obtiene con password grant del
cliente confidencial del realm ``m3``. Las variables se leen del entorno y, si
no est\u00e1n definidas, se completan desde el archivo ``.env`` de la ra\u00edz sin
pisar valores ya presentes.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import pytest

RAIZ_REPO = Path(__file__).resolve().parents[3]


def _cargar_env(ruta: Path) -> None:
    """Carga un ``.env`` sencillo sin sobreescribir variables del proceso."""

    if not ruta.is_file():
        return

    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue

        clave, valor = linea.split("=", 1)
        clave = clave.removeprefix("export ").strip()
        os.environ.setdefault(clave, valor.strip().strip("\"'"))


@dataclass(frozen=True)
class ConfiguracionE2E:
    api_url: str
    keycloak_url: str
    realm: str
    client_id: str
    client_secret: str = field(repr=False)
    operador_username: str
    operador_password: str = field(repr=False)
    conductor_username: str
    conductor_password: str = field(repr=False)
    servicio_username: str
    servicio_password: str = field(repr=False)


def _url_base(nombre: str, puerto: str, por_defecto: str) -> str:
    valor = os.getenv(nombre)
    if valor:
        return valor.rstrip("/")
    return f"http://localhost:{os.getenv(puerto, por_defecto)}"


@pytest.fixture(scope="session")
def configuracion_e2e() -> ConfiguracionE2E:
    _cargar_env(RAIZ_REPO / ".env")

    faltantes = [
        nombre
        for nombre in (
            "KEYCLOAK_M3_CLIENT_SECRET",
            "M3_OPERADOR_PASSWORD",
            "M3_CONDUCTOR_PASSWORD",
            "M3_SERVICIO_PASSWORD",
        )
        if not os.getenv(nombre)
    ]
    if faltantes:
        pytest.fail(
            "Faltan variables para las pruebas E2E: "
            + ", ".join(faltantes)
            + ". Copie .env.example a .env y complete los valores."
        )

    return ConfiguracionE2E(
        api_url=_url_base("API_URL", "API_PORT", "8080"),
        keycloak_url=_url_base("KEYCLOAK_PUBLIC_URL", "KEYCLOAK_PORT", "8081"),
        realm=os.getenv("KEYCLOAK_REALM", "m3"),
        client_id=os.getenv("KEYCLOAK_M3_CLIENT_ID", "m3-api"),
        client_secret=os.environ["KEYCLOAK_M3_CLIENT_SECRET"],
        operador_username=os.getenv("M3_OPERADOR_USERNAME", "operador.m3"),
        operador_password=os.environ["M3_OPERADOR_PASSWORD"],
        conductor_username=os.getenv("M3_CONDUCTOR_USERNAME", "conductor.m3"),
        conductor_password=os.environ["M3_CONDUCTOR_PASSWORD"],
        servicio_username=os.getenv("M3_SERVICIO_USERNAME", "servicio.m4"),
        servicio_password=os.environ["M3_SERVICIO_PASSWORD"],
    )


def _obtener_token(
    configuracion: ConfiguracionE2E,
    *,
    username: str,
    password: str,
) -> str:
    respuesta = httpx.post(
        f"{configuracion.keycloak_url}/realms/{configuracion.realm}/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": configuracion.client_id,
            "client_secret": configuracion.client_secret,
            "username": username,
            "password": password,
        },
        timeout=30.0,
    )
    assert respuesta.status_code == 200, (
        f"Keycloak rechaz\u00f3 el password grant para {username}: "
        f"{respuesta.status_code} {respuesta.text}"
    )
    return respuesta.json()["access_token"]


@pytest.fixture(scope="session")
def cliente_api(configuracion_e2e: ConfiguracionE2E) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=configuracion_e2e.api_url, timeout=30.0) as cliente:
        yield cliente


@pytest.fixture(scope="session")
def headers_operador(configuracion_e2e: ConfiguracionE2E) -> dict[str, str]:
    token = _obtener_token(
        configuracion_e2e,
        username=configuracion_e2e.operador_username,
        password=configuracion_e2e.operador_password,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def headers_conductor(configuracion_e2e: ConfiguracionE2E) -> dict[str, str]:
    token = _obtener_token(
        configuracion_e2e,
        username=configuracion_e2e.conductor_username,
        password=configuracion_e2e.conductor_password,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def headers_servicio(configuracion_e2e: ConfiguracionE2E) -> dict[str, str]:
    token = _obtener_token(
        configuracion_e2e,
        username=configuracion_e2e.servicio_username,
        password=configuracion_e2e.servicio_password,
    )
    return {"Authorization": f"Bearer {token}"}
