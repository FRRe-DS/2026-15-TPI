"""Dependencias de acceso: una por patrón de la matriz del contrato."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Annotated, Any

import pytest
from app.api.main import crear_app
from app.api.seguridad import (
    obtener_cliente_jwks,
    requerir_conductor_propio_operador_o_servicio,
    requerir_conductor_propio_u_operador,
    requerir_operador,
    requerir_operador_o_conductor,
    requerir_operador_o_servicio,
)
from app.aplicacion.politicas.acceso import Identidad
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from tests.api.conftest import instalar_limitador_falso


@pytest.fixture
def client_acceso(cliente_jwks: SimpleNamespace, entorno: None) -> TestClient:
    router = APIRouter()
    visitas: list[str] = []

    @router.get("/listado")
    def listado(
        _: Annotated[Identidad, Depends(requerir_operador_o_servicio)],
    ) -> dict[str, str]:
        return {"estado": "ok"}

    @router.get("/escritura/{id_conductor}")
    def escritura(
        id_conductor: int,
        _: Annotated[Identidad, Depends(requerir_conductor_propio_u_operador)],
    ) -> dict[str, int]:
        visitas.append("escritura")
        return {"id_conductor": id_conductor}

    @router.get("/lectura/{id_conductor}")
    def lectura(
        id_conductor: int,
        _: Annotated[Identidad, Depends(requerir_conductor_propio_operador_o_servicio)],
    ) -> dict[str, int]:
        visitas.append("lectura")
        return {"id_conductor": id_conductor}

    @router.get("/alta")
    def alta(
        _: Annotated[Identidad, Depends(requerir_operador_o_conductor)],
    ) -> dict[str, str]:
        return {"estado": "ok"}

    @router.get("/sin-id-en-la-ruta")
    def sin_id_en_la_ruta(
        _: Annotated[Identidad, Depends(requerir_conductor_propio_u_operador)],
    ) -> dict[str, str]:
        visitas.append("sin-id")
        return {"estado": "ok"}

    @router.get("/solo-operador")
    def solo_operador(
        _: Annotated[dict[str, Any], Depends(requerir_operador)],
    ) -> dict[str, str]:
        return {"estado": "ok"}

    app = crear_app(routers=[router])
    app.dependency_overrides[obtener_cliente_jwks] = lambda: cliente_jwks
    instalar_limitador_falso(app)
    with TestClient(app) as test_client:
        test_client.visitas = visitas  # type: ignore[attr-defined]
        yield test_client
    app.dependency_overrides.clear()


def _headers(crear_token, **claims: Any) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token(**claims)}"}


# --- requerir_operador_o_servicio -------------------------------------------


def test_listado_admite_operador_y_servicio(client_acceso, crear_token, headers_servicio) -> None:
    operador = _headers(crear_token, roles=["operador"], id_operador=7)

    assert client_acceso.get("/api/v1/listado", headers=operador).status_code == 200
    assert client_acceso.get("/api/v1/listado", headers=headers_servicio).status_code == 200


def test_listado_rechaza_al_conductor(client_acceso, headers_conductor_de) -> None:
    respuesta = client_acceso.get("/api/v1/listado", headers=headers_conductor_de(1))

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "SIN_PERMISOS"


# --- requerir_conductor_propio_u_operador -----------------------------------


def test_escritura_admite_al_conductor_propio_y_al_operador(
    client_acceso, crear_token, headers_conductor_de
) -> None:
    operador = _headers(crear_token, roles=["operador"], id_operador=7)

    propio = client_acceso.get("/api/v1/escritura/3", headers=headers_conductor_de(3))
    ajeno = client_acceso.get("/api/v1/escritura/3", headers=operador)

    assert propio.status_code == 200
    assert ajeno.status_code == 200


def test_escritura_rechaza_al_servicio_con_sin_permisos(client_acceso, headers_servicio) -> None:
    respuesta = client_acceso.get("/api/v1/escritura/3", headers=headers_servicio)

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "SIN_PERMISOS"
    assert client_acceso.visitas == []


def test_escritura_rechaza_al_conductor_ajeno_antes_de_buscar_el_recurso(
    client_acceso, headers_conductor_de
) -> None:
    respuesta = client_acceso.get("/api/v1/escritura/99", headers=headers_conductor_de(3))

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "ACCESO_PROHIBIDO"
    assert client_acceso.visitas == []


def test_escritura_rechaza_al_conductor_sin_id_numerico(client_acceso, crear_token) -> None:
    sin_id = _headers(crear_token, roles=["conductor"])
    booleano = _headers(crear_token, roles=["conductor"], id_conductor=True)

    for headers in (sin_id, booleano):
        respuesta = client_acceso.get("/api/v1/escritura/1", headers=headers)
        assert respuesta.status_code == 403
        assert respuesta.json()["codigo"] == "ACCESO_PROHIBIDO"


def test_con_varios_roles_vale_lo_que_permita_cualquiera(client_acceso, crear_token) -> None:
    headers = _headers(crear_token, roles=["conductor", "operador"], id_conductor=3, id_operador=7)

    respuesta = client_acceso.get("/api/v1/escritura/99", headers=headers)

    assert respuesta.status_code == 200


# --- requerir_conductor_propio_operador_o_servicio --------------------------


def test_lectura_admite_propio_operador_y_servicio(
    client_acceso, crear_token, headers_conductor_de, headers_servicio
) -> None:
    operador = _headers(crear_token, roles=["operador"], id_operador=7)

    for headers in (headers_conductor_de(3), operador, headers_servicio):
        assert client_acceso.get("/api/v1/lectura/3", headers=headers).status_code == 200


def test_lectura_rechaza_al_conductor_ajeno_antes_de_buscar_el_recurso(
    client_acceso, headers_conductor_de
) -> None:
    respuesta = client_acceso.get("/api/v1/lectura/99", headers=headers_conductor_de(3))

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "ACCESO_PROHIBIDO"
    assert client_acceso.visitas == []


# --- requerir_operador (sin cambios) ----------------------------------------


def test_requerir_operador_sigue_exigiendo_operador_con_id(
    client_acceso, crear_token, headers_servicio
) -> None:
    operador = _headers(crear_token, roles=["operador"], id_operador=7)

    assert client_acceso.get("/api/v1/solo-operador", headers=operador).status_code == 200
    rechazado = client_acceso.get("/api/v1/solo-operador", headers=headers_servicio)
    assert rechazado.status_code == 403
    assert rechazado.json()["codigo"] == "SIN_PERMISOS"


# --- requerir_operador_o_conductor (alta) ------------------------------------


def test_alta_admite_operador_y_conductor_y_rechaza_al_servicio(
    client_acceso, crear_token, headers_conductor_de, headers_servicio
) -> None:
    operador = _headers(crear_token, roles=["operador"], id_operador=7)

    assert client_acceso.get("/api/v1/alta", headers=operador).status_code == 200
    assert client_acceso.get("/api/v1/alta", headers=headers_conductor_de(1)).status_code == 200
    rechazado = client_acceso.get("/api/v1/alta", headers=headers_servicio)
    assert rechazado.status_code == 403
    assert rechazado.json()["codigo"] == "SIN_PERMISOS"


# --- el id sale de la ruta, nunca de la consulta -------------------------------


def test_el_id_no_se_toma_de_la_consulta_si_la_ruta_no_lo_tiene(
    client_acceso, headers_conductor_de
) -> None:
    respuesta = client_acceso.get(
        "/api/v1/sin-id-en-la-ruta?id_conductor=3", headers=headers_conductor_de(3)
    )

    assert respuesta.status_code != 200
    assert client_acceso.visitas == []


def test_la_consulta_no_pisa_el_id_de_la_ruta(client_acceso, headers_conductor_de) -> None:
    respuesta = client_acceso.get(
        "/api/v1/escritura/9?id_conductor=3", headers=headers_conductor_de(3)
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "ACCESO_PROHIBIDO"


# --- lectura: bordes -----------------------------------------------------------


def test_lectura_rechaza_al_conductor_sin_id_numerico(client_acceso, crear_token) -> None:
    for claims in ({}, {"id_conductor": True}):
        headers = _headers(crear_token, roles=["conductor"], **claims)

        respuesta = client_acceso.get("/api/v1/lectura/1", headers=headers)

        assert respuesta.status_code == 403
        assert respuesta.json()["codigo"] == "ACCESO_PROHIBIDO"


def test_lectura_de_conductor_y_servicio_pasa_sobre_un_id_ajeno(client_acceso, crear_token) -> None:
    headers = _headers(crear_token, roles=["conductor", "servicio"], id_conductor=3)

    respuesta = client_acceso.get("/api/v1/lectura/99", headers=headers)

    assert respuesta.status_code == 200
