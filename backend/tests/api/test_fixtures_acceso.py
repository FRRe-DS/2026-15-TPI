"""Verifica el contenido de los tokens que fabrican las fixtures de acceso."""

from __future__ import annotations

from typing import Any

import jwt


def _payload(headers: dict[str, str]) -> dict[str, Any]:
    token = headers["Authorization"].removeprefix("Bearer ")
    return jwt.decode(token, options={"verify_signature": False})


def test_crear_token_incluye_sub_de_texto_no_vacio_por_defecto(crear_token) -> None:
    payload = jwt.decode(crear_token(), options={"verify_signature": False})

    assert isinstance(payload["sub"], str)
    assert payload["sub"]
    assert payload["iss"]


def test_crear_token_acepta_varios_roles_e_id_conductor(crear_token) -> None:
    token = crear_token(roles=["conductor", "operador"], id_conductor=4, id_operador=7)

    payload = jwt.decode(token, options={"verify_signature": False})

    assert payload["realm_access"]["roles"] == ["conductor", "operador"]
    assert payload["id_conductor"] == 4
    assert payload["id_operador"] == 7


def test_crear_token_sin_id_conductor_no_incluye_el_claim(crear_token) -> None:
    payload = jwt.decode(crear_token(), options={"verify_signature": False})

    assert "id_conductor" not in payload


def test_fixtures_de_acceso(headers_servicio, headers_conductor_de) -> None:
    servicio = _payload(headers_servicio)
    conductor = _payload(headers_conductor_de(9))

    assert servicio["realm_access"]["roles"] == ["servicio"]
    assert "id_conductor" not in servicio
    assert "id_operador" not in servicio
    assert conductor["realm_access"]["roles"] == ["conductor"]
    assert conductor["id_conductor"] == 9
    assert servicio["sub"]
    assert conductor["sub"]
