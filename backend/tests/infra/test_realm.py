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


def test_realm_m3_con_roles_operador_conductor_y_servicio() -> None:
    realm = _cargar()
    assert realm["realm"] == "m3"
    roles = {rol["name"] for rol in realm["roles"]["realm"]}
    assert {"operador", "conductor", "servicio"} <= roles


def _usuario_con_rol(realm: dict[str, Any], rol: str) -> dict[str, Any]:
    for usuario in realm["users"]:
        if rol in usuario.get("realmRoles", []):
            return usuario
    raise AssertionError(f"No hay un usuario con el rol {rol!r}")


def test_cuenta_tecnica_servicio_parametrizada_por_entorno() -> None:
    realm = _cargar()
    rol = next(rol for rol in realm["roles"]["realm"] if rol["name"] == "servicio")
    assert rol["composite"] is False

    servicio = _usuario_con_rol(realm, "servicio")
    assert servicio["realmRoles"] == ["servicio"], "La cuenta tecnica no debe tener otros roles"
    assert servicio["enabled"] is True
    assert servicio["username"] == "${M3_SERVICIO_USERNAME}"
    assert PLACEHOLDER.match(servicio["username"])

    assert len(servicio["credentials"]) == 1
    credencial = servicio["credentials"][0]
    assert credencial["type"] == "password"
    assert credencial["value"] == "${M3_SERVICIO_PASSWORD}"
    assert PLACEHOLDER.match(credencial["value"])


def test_el_usuario_conductor_apunta_a_un_conductor_del_seed(seed_module: Any) -> None:
    realm = _cargar()
    conductor = next(u for u in realm["users"] if u["username"] == "conductor.m3")
    valores = conductor["attributes"]["id_conductor"]

    assert len(valores) == 1
    assert int(valores[0]) == seed_module.ID_CONDUCTOR_PRUEBA
    assert seed_module.CONDUCTORES[0]["dni"] == seed_module.DNI_CONDUCTOR_PRUEBA


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


def _perfil_de_usuario(realm: dict[str, Any]) -> dict[str, Any]:
    componente = realm["components"]["org.keycloak.userprofile.UserProfileProvider"][0]
    assert componente["providerId"] == "declarative-user-profile"

    return json.loads(componente["config"]["kc.user.profile.config"][0])


def test_el_user_profile_declara_los_claims_numericos() -> None:
    perfil = _perfil_de_usuario(_cargar())
    atributos = {atributo["name"]: atributo for atributo in perfil["attributes"]}

    assert {"username", "email", "firstName", "lastName"} <= atributos.keys()
    for nombre in ("id_operador", "id_conductor"):
        atributo = atributos[nombre]
        assert atributo["multivalued"] is False
        assert "integer" in atributo["validations"]

    cliente = next(c for c in _cargar()["clients"] if c["clientId"] == "m3-api")
    mappers = {
        mapper["config"]["user.attribute"]: mapper
        for mapper in cliente["protocolMappers"]
        if mapper["config"].get("claim.name") == mapper["config"].get("user.attribute")
    }
    assert {"id_operador", "id_conductor"} <= mappers.keys()
    assert all(mapper["config"]["jsonType.label"] == "int" for mapper in mappers.values())


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
