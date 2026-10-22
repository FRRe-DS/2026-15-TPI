"""T086b: un token real de Keycloak trae los IDs como enteros.

Levanta Keycloak con Testcontainers, importa el realm y pide un token con
concesión de contraseña. El test se omite si Docker no está disponible.
"""

from __future__ import annotations

import base64
import json
import urllib.parse
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

REALM = Path(__file__).resolve().parents[3] / "infra" / "keycloak" / "realm-m3.json"
CLIENTE = "m3-api"
SECRETO_CLIENTE = "test-client-secret-no-real"
CLAVE_OPERADOR = "test-operador-no-real"
CLAVE_CONDUCTOR = "test-conductor-no-real"

pytestmark = pytest.mark.integration


def _realm_para_prueba(destino: Path) -> Path:
    contenido = REALM.read_text(encoding="utf-8")
    reemplazos = {
        "KEYCLOAK_M3_CLIENT_SECRET": SECRETO_CLIENTE,
        "M3_OPERADOR_PASSWORD": CLAVE_OPERADOR,
        "M3_CONDUCTOR_PASSWORD": CLAVE_CONDUCTOR,
    }
    for variable, valor in reemplazos.items():
        contenido = contenido.replace(f"${{{variable}}}", valor)

    assert all(f"${{{variable}}}" not in contenido for variable in reemplazos)
    destino.write_text(contenido, encoding="utf-8")
    return destino


def _token(base: str, usuario: str, clave: str) -> str:
    datos = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": CLIENTE,
            "client_secret": SECRETO_CLIENTE,
            "username": usuario,
            "password": clave,
        }
    ).encode()
    peticion = urllib.request.Request(
        f"{base}/realms/m3/protocol/openid-connect/token",
        data=datos,
    )
    with urllib.request.urlopen(peticion, timeout=10) as respuesta:
        return json.load(respuesta)["access_token"]


def _claims(token: str) -> dict[str, object]:
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


@pytest.fixture(scope="module")
def keycloak(requiere_docker: None, tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    from testcontainers.core.container import DockerContainer
    from testcontainers.core.wait_strategies import HttpWaitStrategy

    realm = _realm_para_prueba(tmp_path_factory.mktemp("keycloak") / "realm-m3.json")
    contenedor = DockerContainer("quay.io/keycloak/keycloak:26.8.1")
    contenedor.with_command("start-dev --import-realm")
    contenedor.with_exposed_ports(8080)
    contenedor.with_volume_mapping(
        str(realm), "/opt/keycloak/data/import/realm-m3.json", "ro"
    )
    contenedor.waiting_for(HttpWaitStrategy(8080, "/realms/m3").for_status_code(200))
    contenedor.start()
    try:
        host = contenedor.get_container_host_ip()
        puerto = contenedor.get_exposed_port(8080)
        yield f"http://{host}:{puerto}"
    finally:
        contenedor.stop()


def test_el_token_real_trae_los_ids_como_enteros(keycloak: str) -> None:
    operador = _claims(_token(keycloak, "operador.m3", CLAVE_OPERADOR))
    assert operador["id_operador"] == 101
    assert isinstance(operador["id_operador"], int)

    conductor = _claims(_token(keycloak, "conductor.m3", CLAVE_CONDUCTOR))
    assert conductor["id_conductor"] == 1
    assert isinstance(conductor["id_conductor"], int)
