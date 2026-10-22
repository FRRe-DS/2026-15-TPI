"""T086: contrato del realm de Keycloak y ausencia de secretos literales."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REALM = Path(__file__).resolve().parents[3] / "infra" / "keycloak" / "realm-m3.json"
PLACEHOLDER = re.compile(r"^\$\{[A-Z0-9_]+\}$")


def _cargar() -> dict[str, Any]:
    return json.loads(REALM.read_text(encoding="utf-8"))


def _valores_por_clave(nodo: Any, claves: set[str]) -> list[Any]:
    encontrados: list[Any] = []
    if isinstance(nodo, dict):
        for clave, valor in nodo.items():
            if clave.lower() in claves:
                encontrados.append(valor)
            encontrados.extend(_valores_por_clave(valor, claves))
    elif isinstance(nodo, list):
        for item in nodo:
            encontrados.extend(_valores_por_clave(item, claves))
    return encontrados


def test_el_realm_es_json_valido() -> None:
    assert isinstance(_cargar(), dict)


def test_realm_m3_con_roles_operador_y_conductor() -> None:
    realm = _cargar()
    assert realm["realm"] == "m3"
    roles = {rol["name"] for rol in realm["roles"]["realm"]}
    assert {"operador", "conductor"} <= roles


def test_cliente_confidencial_con_password_grant() -> None:
    realm = _cargar()
    cliente = next(c for c in realm["clients"] if c["clientId"] == "m3-api")

    assert cliente["publicClient"] is False
    assert cliente["clientAuthenticatorType"] == "client-secret"
    assert cliente["directAccessGrantsEnabled"] is True
    assert PLACEHOLDER.match(cliente["secret"]), "El secreto debe venir de una variable"


def test_usuario_operador_con_id_operador_numerico_y_claim_entero() -> None:
    realm = _cargar()
    operador = next(u for u in realm["users"] if u["username"] == "operador.m3")

    assert "operador" in operador["realmRoles"]
    valores = operador["attributes"]["id_operador"]
    assert isinstance(valores, list) and valores
    assert all(str(valor).isdigit() for valor in valores)

    cliente = next(c for c in realm["clients"] if c["clientId"] == "m3-api")
    mapper = next(
        m for m in cliente["protocolMappers"] if m["config"].get("user.attribute") == "id_operador"
    )
    config = mapper["config"]

    assert mapper["protocolMapper"] == "oidc-usermodel-attribute-mapper"
    assert config["claim.name"] == "id_operador"
    assert config["jsonType.label"] in {"int", "long"}
    assert config["access.token.claim"] == "true"


def test_no_hay_password_ni_secretos_literales() -> None:
    realm = _cargar()

    for credencial in (
        credencial for usuario in realm["users"] for credencial in usuario["credentials"]
    ):
        assert credencial["type"] == "password"
        assert PLACEHOLDER.match(credencial["value"])

    for valor in _valores_por_clave(realm, {"secret", "password", "clave", "clientsecret"}):
        assert isinstance(valor, str)
        assert PLACEHOLDER.match(valor), f"Valor literal detectado: {valor!r}"


def test_los_usuarios_de_prueba_tienen_credenciales_por_variable() -> None:
    realm = _cargar()
    usuarios = {usuario["username"] for usuario in realm["users"]}

    assert {"operador.m3", "conductor.m3"} <= usuarios
    for usuario in realm["users"]:
        assert usuario["enabled"] is True
        assert usuario["credentials"]
