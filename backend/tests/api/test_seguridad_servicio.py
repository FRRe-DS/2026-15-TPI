"""El rol servicio y el claim id_conductor llegan a la Identidad del token."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Annotated, Any

import pytest
from app.api.main import crear_app
from app.api.seguridad import (
    ROLES_VALIDOS,
    obtener_cliente_jwks,
    requerir_identidad,
    requerir_usuario,
)
from app.aplicacion.politicas.acceso import Identidad
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from tests.api.conftest import instalar_limitador_falso

URL_USUARIO = "/api/v1/usuario"
URL_IDENTIDAD = "/api/v1/identidad"


@pytest.fixture
def client_identidad(cliente_jwks: SimpleNamespace, entorno: None) -> TestClient:
    router = APIRouter()

    @router.get("/usuario")
    def usuario(
        _: Annotated[dict[str, Any], Depends(requerir_usuario)],
    ) -> dict[str, str]:
        return {"estado": "ok"}

    @router.get("/identidad")
    def identidad(
        identidad: Annotated[Identidad, Depends(requerir_identidad)],
    ) -> dict[str, Any]:
        return {
            "roles": sorted(identidad.roles),
            "id_conductor": identidad.id_conductor,
            "id_operador": identidad.id_operador,
        }

    app = crear_app(routers=[router])
    app.dependency_overrides[obtener_cliente_jwks] = lambda: cliente_jwks
    instalar_limitador_falso(app)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_servicio_es_un_rol_valido() -> None:
    assert ROLES_VALIDOS == {"conductor", "operador", "servicio"}


def test_token_con_solo_rol_servicio_es_aceptado(
    client_identidad: TestClient,
    headers_servicio: dict[str, str],
) -> None:
    respuesta = client_identidad.get(URL_USUARIO, headers=headers_servicio)

    assert respuesta.status_code == 200


def test_token_sin_ningun_rol_reconocido_responde_403(
    client_identidad: TestClient,
    crear_token,
) -> None:
    token = crear_token(roles=["otro-rol"])

    respuesta = client_identidad.get(URL_USUARIO, headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "SIN_PERMISOS"


def test_la_identidad_lee_roles_y_claim_id_conductor_entero(
    client_identidad: TestClient,
    headers_conductor_de,
) -> None:
    respuesta = client_identidad.get(URL_IDENTIDAD, headers=headers_conductor_de(5))

    assert respuesta.json() == {
        "roles": ["conductor"],
        "id_conductor": 5,
        "id_operador": None,
    }


def test_la_identidad_lee_id_operador_y_varios_roles(
    client_identidad: TestClient,
    crear_token,
) -> None:
    token = crear_token(roles=["operador", "conductor"], id_operador=7, id_conductor=2)

    respuesta = client_identidad.get(URL_IDENTIDAD, headers={"Authorization": f"Bearer {token}"})

    assert respuesta.json() == {
        "roles": ["conductor", "operador"],
        "id_conductor": 2,
        "id_operador": 7,
    }


@pytest.mark.parametrize(
    "id_conductor",
    [True, "no-numerico", 3.5],
    ids=["booleano", "no-numerico", "decimal"],
)
def test_id_conductor_invalido_se_trata_como_ausente(
    client_identidad: TestClient,
    crear_token,
    id_conductor: Any,
) -> None:
    token = crear_token(roles=["conductor"], id_conductor=id_conductor)

    respuesta = client_identidad.get(URL_IDENTIDAD, headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.json()["id_conductor"] is None
