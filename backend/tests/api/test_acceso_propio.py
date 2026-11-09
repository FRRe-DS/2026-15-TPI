"""Acceso por rol y propio en los endpoints de la Iteración 1 (matriz del contrato)."""

from __future__ import annotations

from typing import Any

import pytest

from tests.api.test_conductores_crear import PAYLOAD as ALTA_CONDUCTOR
from tests.api.test_documentacion_licencia import PAYLOAD as LICENCIA
from tests.api.test_vehiculos_crear import PAYLOAD as VEHICULO

BASE = "/api/v1/conductores"
ACCION = {"accion": "APROBAR", "motivo": "Prueba"}

# (id, método, ruta con {id}, cuerpo, caso de uso, ¿lo lee el servicio?)
OPERACIONES_POR_CONDUCTOR = [
    pytest.param("get", BASE + "/{id}", None, "obtener_conductor", True, id="3-obtener"),
    pytest.param(
        "get",
        BASE + "/{id}/habilitacion",
        None,
        "consultar_habilitacion_conductor",
        True,
        id="4-habilitacion",
    ),
    pytest.param(
        "post",
        BASE + "/{id}/documentacion",
        LICENCIA,
        "registrar_licencia",
        False,
        id="6-documentacion",
    ),
    pytest.param(
        "post",
        BASE + "/{id}/vehiculos",
        VEHICULO,
        "registrar_vehiculo",
        False,
        id="7-vehiculo-alta",
    ),
    pytest.param("get", BASE + "/{id}/vehiculos", None, "listar_vehiculos", True, id="8-vehiculos"),
    pytest.param(
        "get", BASE + "/{id}/vehiculos/5", None, "obtener_vehiculo", True, id="9-vehiculo"
    ),
]


def _pedir(client, metodo: str, ruta: str, cuerpo: Any, headers: dict[str, str]):
    if cuerpo is None:
        return getattr(client, metodo)(ruta, headers=headers)
    return getattr(client, metodo)(ruta, json=cuerpo, headers=headers)


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo", "caso", "_lee"), OPERACIONES_POR_CONDUCTOR)
def test_el_conductor_opera_sobre_su_propio_id(
    client, casos, headers_conductor_de, metodo, ruta, cuerpo, caso, _lee
) -> None:
    respuesta = _pedir(client, metodo, ruta.format(id=1), cuerpo, headers_conductor_de(1))

    assert respuesta.status_code in (200, 201)
    assert len(casos[caso].llamadas) == 1


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo", "caso", "_lee"), OPERACIONES_POR_CONDUCTOR)
def test_el_conductor_con_el_id_de_otro_recibe_403_sin_llamar_al_caso_de_uso(
    client, casos, headers_conductor_de, metodo, ruta, cuerpo, caso, _lee
) -> None:
    # El id 99 no existe: aun así la respuesta es 403 y no 404.
    respuesta = _pedir(client, metodo, ruta.format(id=99), cuerpo, headers_conductor_de(1))

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "ACCESO_PROHIBIDO"
    assert casos[caso].llamadas == []


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo", "caso", "_lee"), OPERACIONES_POR_CONDUCTOR)
def test_el_conductor_sin_id_conductor_numerico_recibe_403(
    client, casos, crear_token, metodo, ruta, cuerpo, caso, _lee
) -> None:
    for claims in ({}, {"id_conductor": True}):
        headers = {"Authorization": f"Bearer {crear_token(roles=['conductor'], **claims)}"}

        respuesta = _pedir(client, metodo, ruta.format(id=1), cuerpo, headers)

        assert respuesta.status_code == 403
        assert respuesta.json()["codigo"] == "ACCESO_PROHIBIDO"
    assert casos[caso].llamadas == []


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo", "caso", "_lee"), OPERACIONES_POR_CONDUCTOR)
def test_el_operador_accede_a_cualquier_conductor(
    client, casos, headers_operador, metodo, ruta, cuerpo, caso, _lee
) -> None:
    respuesta = _pedir(client, metodo, ruta.format(id=99), cuerpo, headers_operador)

    assert respuesta.status_code in (200, 201)
    assert len(casos[caso].llamadas) == 1


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo", "caso", "lee"), OPERACIONES_POR_CONDUCTOR)
def test_el_servicio_solo_lee(
    client, casos, headers_servicio, metodo, ruta, cuerpo, caso, lee
) -> None:
    respuesta = _pedir(client, metodo, ruta.format(id=99), cuerpo, headers_servicio)

    if lee:
        assert respuesta.status_code == 200
        assert len(casos[caso].llamadas) == 1
    else:
        assert respuesta.status_code == 403
        assert respuesta.json()["codigo"] == "SIN_PERMISOS"
        assert casos[caso].llamadas == []


# --- Operación 1: alta de conductor ------------------------------------------


def test_el_servicio_no_da_altas(client, casos, headers_servicio) -> None:
    respuesta = client.post(BASE, json=ALTA_CONDUCTOR, headers=headers_servicio)

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "SIN_PERMISOS"
    assert casos["crear_conductor"].llamadas == []


def test_el_operador_y_el_conductor_dan_altas(
    client, casos, headers_operador, headers_conductor_de
) -> None:
    for headers in (headers_operador, headers_conductor_de(1)):
        respuesta = client.post(BASE, json=ALTA_CONDUCTOR, headers=headers)
        assert respuesta.status_code == 201
    assert len(casos["crear_conductor"].llamadas) == 2


# --- Operaciones 5 y 10: habilitaciones, solo del operador --------------------


@pytest.mark.parametrize(
    ("ruta", "caso"),
    [
        (BASE + "/1/habilitacion", "accionar_habilitacion_conductor"),
        (BASE + "/1/vehiculos/5/habilitacion", "accionar_habilitacion_vehiculo"),
    ],
    ids=["5-conductor", "10-vehiculo"],
)
def test_las_habilitaciones_siguen_siendo_solo_del_operador(
    client, casos, headers_conductor_de, headers_servicio, headers_operador, ruta, caso
) -> None:
    for headers in (headers_conductor_de(1), headers_servicio):
        respuesta = client.post(ruta, json=ACCION, headers=headers)
        assert respuesta.status_code == 403
        assert respuesta.json()["codigo"] == "SIN_PERMISOS"
    assert casos[caso].llamadas == []

    assert client.post(ruta, json=ACCION, headers=headers_operador).status_code == 200


# --- Operación 2: listado -------------------------------------------------------


def test_el_listado_es_del_operador_y_del_servicio(
    client, casos, headers_conductor_de, headers_operador, headers_servicio
) -> None:
    rechazado = client.get(BASE, headers=headers_conductor_de(1))

    assert rechazado.status_code == 403
    assert rechazado.json()["codigo"] == "SIN_PERMISOS"
    assert casos["listar_conductores"].llamadas == []
    assert client.get(BASE, headers=headers_operador).status_code == 200
    assert client.get(BASE, headers=headers_servicio).status_code == 200
