"""Endpoints de estado y ubicación del conductor (operaciones 13, 14 y 15)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from app.api import dependencias
from app.api.main import crear_app
from app.api.seguridad import obtener_cliente_jwks
from app.aplicacion.casos_de_uso.resultados import EstadoDelConductor, UbicacionDelConductor
from app.dominio.conductor import EstadoConductor
from app.dominio.disponibilidad import NO_INFORMADO
from app.dominio.errores import ConductorNoHabilitado, NoEncontrado
from fastapi.testclient import TestClient

from tests.api.conftest import CasoDeUsoFalso, devolver_caso

ESTADO = "/api/v1/conductores/{id}/estado"
UBICACION = "/api/v1/conductores/{id}/ubicacion"
FECHA = datetime(2026, 11, 2, 1, 30, tzinfo=UTC)

PROVEEDORES_V3 = {
    "obtener_estado": "obtener_caso_obtener_estado_conductor",
    "obtener_ubicacion": "obtener_caso_obtener_ubicacion_conductor",
    "actualizar_estado": "obtener_caso_actualizar_estado_conductor",
}


@pytest.fixture
def casos_estado() -> dict[str, CasoDeUsoFalso]:
    estado = EstadoDelConductor(
        id_conductor=1,
        estado=EstadoConductor.DISPONIBLE,
        id_vehiculo_activo=5,
        actualizado=FECHA,
    )
    ubicacion = UbicacionDelConductor(
        id_conductor=1, latitud=-27.4511, longitud=-58.9867, fecha_act_ubic=FECHA
    )
    return {
        "obtener_estado": CasoDeUsoFalso(estado),
        "obtener_ubicacion": CasoDeUsoFalso(ubicacion),
        "actualizar_estado": CasoDeUsoFalso(estado),
    }


@pytest.fixture
def client_estado(
    casos_estado: dict[str, CasoDeUsoFalso],
    cliente_jwks: SimpleNamespace,
    entorno: None,
) -> TestClient:
    app = crear_app()
    app.dependency_overrides[obtener_cliente_jwks] = lambda: cliente_jwks
    for clave, nombre in PROVEEDORES_V3.items():
        app.dependency_overrides[getattr(dependencias, nombre)] = devolver_caso(casos_estado[clave])
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# --- GET estado -----------------------------------------------------------------


def test_obtener_estado_devuelve_el_estado_sin_ubicacion(
    client_estado, casos_estado, headers_conductor_de
) -> None:
    respuesta = client_estado.get(ESTADO.format(id=1), headers=headers_conductor_de(1))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id_conductor": 1,
        "estado": "DISPONIBLE",
        "id_vehiculo_activo": 5,
        "actualizado": "2026-11-02T01:30:00Z",
    }
    assert casos_estado["obtener_estado"].llamadas == [{"id_conductor": 1}]


def test_obtener_estado_lo_leen_operador_servicio_y_el_propio_conductor(
    client_estado, headers_operador, headers_servicio, headers_conductor_de
) -> None:
    for headers in (headers_operador, headers_servicio, headers_conductor_de(1)):
        assert client_estado.get(ESTADO.format(id=1), headers=headers).status_code == 200


def test_obtener_estado_de_otro_conductor_es_403_sin_llamar_al_caso(
    client_estado, casos_estado, headers_conductor_de
) -> None:
    respuesta = client_estado.get(ESTADO.format(id=99), headers=headers_conductor_de(1))

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "ACCESO_PROHIBIDO"
    assert casos_estado["obtener_estado"].llamadas == []


def test_obtener_estado_inexistente_es_404(client_estado, casos_estado, headers_operador) -> None:
    casos_estado["obtener_estado"].error = NoEncontrado("No existe el conductor 99")

    respuesta = client_estado.get(ESTADO.format(id=99), headers=headers_operador)

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"


# --- GET ubicación ----------------------------------------------------------------


def test_obtener_ubicacion_devuelve_la_ultima_registrada(
    client_estado, casos_estado, headers_conductor_de
) -> None:
    respuesta = client_estado.get(UBICACION.format(id=1), headers=headers_conductor_de(1))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id_conductor": 1,
        "latitud": -27.4511,
        "longitud": -58.9867,
        "fecha_act_ubic": "2026-11-02T01:30:00Z",
    }
    assert casos_estado["obtener_ubicacion"].llamadas == [{"id_conductor": 1}]


def test_obtener_ubicacion_sin_registro_responde_200_con_nulos(
    client_estado, casos_estado, headers_servicio
) -> None:
    casos_estado["obtener_ubicacion"].resultado = UbicacionDelConductor(
        id_conductor=1, latitud=None, longitud=None, fecha_act_ubic=None
    )

    respuesta = client_estado.get(UBICACION.format(id=1), headers=headers_servicio)

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id_conductor": 1,
        "latitud": None,
        "longitud": None,
        "fecha_act_ubic": None,
    }


def test_obtener_ubicacion_de_otro_conductor_es_403(
    client_estado, casos_estado, headers_conductor_de
) -> None:
    respuesta = client_estado.get(UBICACION.format(id=99), headers=headers_conductor_de(1))

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "ACCESO_PROHIBIDO"
    assert casos_estado["obtener_ubicacion"].llamadas == []


def test_obtener_ubicacion_inexistente_es_404(
    client_estado, casos_estado, headers_operador
) -> None:
    casos_estado["obtener_ubicacion"].error = NoEncontrado("No existe el conductor 99")

    respuesta = client_estado.get(UBICACION.format(id=99), headers=headers_operador)

    assert respuesta.status_code == 404


# --- PATCH estado -------------------------------------------------------------------


def test_actualizar_estado_pasa_los_argumentos_esperados(
    client_estado, casos_estado, headers_conductor_de
) -> None:
    cuerpo = {
        "estado": "DISPONIBLE",
        "id_vehiculo_activo": 5,
        "latitud": -27.1,
        "longitud": -58.2,
    }

    respuesta = client_estado.patch(
        ESTADO.format(id=1), json=cuerpo, headers=headers_conductor_de(1)
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "DISPONIBLE"
    assert casos_estado["actualizar_estado"].llamadas == [
        {
            "id_conductor": 1,
            "estado": EstadoConductor.DISPONIBLE,
            "id_vehiculo_activo": 5,
            "latitud": -27.1,
            "longitud": -58.2,
        }
    ]


def test_actualizar_estado_con_solo_estado_deja_el_resto_sin_informar(
    client_estado, casos_estado, headers_operador
) -> None:
    client_estado.patch(ESTADO.format(id=1), json={"estado": "CONECTADO"}, headers=headers_operador)

    llamada = casos_estado["actualizar_estado"].llamadas[0]
    assert llamada["estado"] is EstadoConductor.CONECTADO
    assert llamada["id_vehiculo_activo"] is NO_INFORMADO
    assert llamada["latitud"] is None
    assert llamada["longitud"] is None


def test_actualizar_estado_distingue_vehiculo_nulo_de_no_informado(
    client_estado, casos_estado, headers_operador
) -> None:
    client_estado.patch(
        ESTADO.format(id=1), json={"id_vehiculo_activo": None}, headers=headers_operador
    )

    llamada = casos_estado["actualizar_estado"].llamadas[0]
    assert llamada["estado"] is None
    assert llamada["id_vehiculo_activo"] is None


@pytest.mark.parametrize(
    "cuerpo",
    [
        {},
        {"latitud": -27.1},
        {"longitud": -58.2},
        {"estado": "OCUPADO"},
        {"estado": None},
        {"latitud": None, "longitud": None},
    ],
    ids=["vacio", "solo-latitud", "solo-longitud", "ocupado", "estado-nulo", "coordenadas-nulas"],
)
def test_actualizar_estado_con_pedido_invalido_es_400(
    client_estado, casos_estado, headers_operador, cuerpo
) -> None:
    respuesta = client_estado.patch(ESTADO.format(id=1), json=cuerpo, headers=headers_operador)

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert casos_estado["actualizar_estado"].llamadas == []


def test_actualizar_estado_de_conductor_no_habilitado_es_422(
    client_estado, casos_estado, headers_conductor_de
) -> None:
    casos_estado["actualizar_estado"].error = ConductorNoHabilitado("No está habilitado")

    respuesta = client_estado.patch(
        ESTADO.format(id=1), json={"estado": "DISPONIBLE"}, headers=headers_conductor_de(1)
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "CONDUCTOR_NO_HABILITADO"


def test_actualizar_estado_inexistente_es_404(
    client_estado, casos_estado, headers_operador
) -> None:
    casos_estado["actualizar_estado"].error = NoEncontrado("No existe el conductor 99")

    respuesta = client_estado.patch(
        ESTADO.format(id=99), json={"estado": "CONECTADO"}, headers=headers_operador
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"


def test_actualizar_estado_con_el_rol_servicio_es_403(
    client_estado, casos_estado, headers_servicio
) -> None:
    respuesta = client_estado.patch(
        ESTADO.format(id=1), json={"estado": "CONECTADO"}, headers=headers_servicio
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "SIN_PERMISOS"
    assert casos_estado["actualizar_estado"].llamadas == []


def test_actualizar_estado_de_otro_conductor_es_403(
    client_estado, casos_estado, headers_conductor_de
) -> None:
    respuesta = client_estado.patch(
        ESTADO.format(id=99), json={"estado": "CONECTADO"}, headers=headers_conductor_de(1)
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "ACCESO_PROHIBIDO"
    assert casos_estado["actualizar_estado"].llamadas == []
