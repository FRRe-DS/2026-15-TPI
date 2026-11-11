"""Endpoints de solicitudes (operaciones 16 y 17)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from app.api import dependencias
from app.api.main import crear_app
from app.api.seguridad import obtener_cliente_jwks
from app.aplicacion.politicas.acceso import Identidad
from app.dominio.errores import (
    AccesoProhibido,
    ConductorNoHabilitado,
    NoEncontrado,
    SolicitudVencida,
    SolicitudYaRespondida,
)
from app.dominio.solicitud import EstadoSolicitud, Solicitud
from fastapi.testclient import TestClient

from tests.api.conftest import CasoDeUsoFalso, devolver_caso, instalar_limitador_falso

LISTADO = "/api/v1/conductores/{id}/solicitudes"
RESPONDER = "/api/v1/solicitudes/{id}"
VENCE = datetime(2026, 10, 3, 18, 45, 30, tzinfo=UTC)
HORA_RTA = "2026-10-03T18:44:10Z"
CUERPO = {"respuesta": "ACEPTADO", "hora_rta": HORA_RTA}

PROVEEDORES_V4 = {
    "listar": "obtener_caso_listar_solicitudes_conductor",
    "responder": "obtener_caso_responder_solicitud",
}


def _solicitud(**cambios) -> Solicitud:
    datos = {
        "id": 340,
        "id_conductor": 1,
        "id_viaje": 5521,
        "estado": EstadoSolicitud.PENDIENTE,
        "vence_en": VENCE,
    }
    datos.update(cambios)
    return Solicitud(**datos)


@pytest.fixture
def casos_solicitudes() -> dict[str, CasoDeUsoFalso]:
    aceptada = _solicitud(
        estado=EstadoSolicitud.ACEPTADO,
        respuesta=EstadoSolicitud.ACEPTADO,
        hora_rta=datetime(2026, 10, 3, 18, 44, 10, tzinfo=UTC),
    )
    return {
        "listar": CasoDeUsoFalso([_solicitud()]),
        "responder": CasoDeUsoFalso(aceptada),
    }


@pytest.fixture
def client_solicitudes(
    casos_solicitudes: dict[str, CasoDeUsoFalso],
    cliente_jwks: SimpleNamespace,
    entorno: None,
) -> TestClient:
    app = crear_app()
    app.dependency_overrides[obtener_cliente_jwks] = lambda: cliente_jwks
    instalar_limitador_falso(app)
    for clave, nombre in PROVEEDORES_V4.items():
        app.dependency_overrides[getattr(dependencias, nombre)] = devolver_caso(
            casos_solicitudes[clave]
        )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# --- GET solicitudes del conductor -------------------------------------------------


def test_listar_devuelve_las_solicitudes_del_conductor(
    client_solicitudes, casos_solicitudes, headers_conductor_de
) -> None:
    respuesta = client_solicitudes.get(LISTADO.format(id=1), headers=headers_conductor_de(1))

    assert respuesta.status_code == 200
    assert respuesta.json() == [
        {
            "id": 340,
            "id_conductor": 1,
            "id_viaje": 5521,
            "estado": "PENDIENTE",
            "vence_en": "2026-10-03T18:45:30Z",
            "respuesta": None,
            "hora_rta": None,
        }
    ]
    assert casos_solicitudes["listar"].llamadas == [{"id_conductor": 1, "estado": None}]


def test_listar_serializa_pendientes_vencidas_y_respondidas(
    client_solicitudes, casos_solicitudes, headers_operador
) -> None:
    respondida = _solicitud(
        id=342,
        estado=EstadoSolicitud.RECHAZADO,
        respuesta=EstadoSolicitud.RECHAZADO,
        hora_rta=datetime(2026, 10, 3, 18, 44, 10, tzinfo=UTC),
    )
    casos_solicitudes["listar"].resultado = [
        _solicitud(id=340),
        _solicitud(id=341, estado=EstadoSolicitud.VENCIDA),
        respondida,
    ]

    respuesta = client_solicitudes.get(LISTADO.format(id=1), headers=headers_operador)

    assert respuesta.status_code == 200
    por_id = {solicitud["id"]: solicitud for solicitud in respuesta.json()}
    assert por_id[340]["estado"] == "PENDIENTE"
    assert por_id[341]["estado"] == "VENCIDA"
    assert por_id[341]["respuesta"] is None
    assert por_id[342]["estado"] == "RECHAZADO"
    assert por_id[342]["respuesta"] == "RECHAZADO"
    assert por_id[342]["hora_rta"] == HORA_RTA


def test_listar_admite_el_filtro_estado(
    client_solicitudes, casos_solicitudes, headers_operador
) -> None:
    respuesta = client_solicitudes.get(
        LISTADO.format(id=1), params={"estado": "VENCIDA"}, headers=headers_operador
    )

    assert respuesta.status_code == 200
    assert casos_solicitudes["listar"].llamadas == [
        {"id_conductor": 1, "estado": EstadoSolicitud.VENCIDA}
    ]


def test_listar_con_estado_invalido_es_400(
    client_solicitudes, casos_solicitudes, headers_operador
) -> None:
    respuesta = client_solicitudes.get(
        LISTADO.format(id=1), params={"estado": "CANCELADA"}, headers=headers_operador
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert casos_solicitudes["listar"].llamadas == []


def test_el_conductor_lista_solo_las_suyas(
    client_solicitudes, casos_solicitudes, headers_conductor_de
) -> None:
    respuesta = client_solicitudes.get(LISTADO.format(id=99), headers=headers_conductor_de(1))

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "ACCESO_PROHIBIDO"
    assert casos_solicitudes["listar"].llamadas == []


def test_el_servicio_no_lista_solicitudes(
    client_solicitudes, casos_solicitudes, headers_servicio
) -> None:
    respuesta = client_solicitudes.get(LISTADO.format(id=1), headers=headers_servicio)

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "SIN_PERMISOS"
    assert casos_solicitudes["listar"].llamadas == []


def test_listar_de_un_conductor_inexistente_es_404(
    client_solicitudes, casos_solicitudes, headers_operador
) -> None:
    casos_solicitudes["listar"].error = NoEncontrado("No existe el conductor 99")

    respuesta = client_solicitudes.get(LISTADO.format(id=99), headers=headers_operador)

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"


# --- POST responder -------------------------------------------------------------------


def test_responder_devuelve_la_solicitud_y_pasa_la_identidad(
    client_solicitudes, casos_solicitudes, headers_conductor_de
) -> None:
    respuesta = client_solicitudes.post(
        RESPONDER.format(id=340), json=CUERPO, headers=headers_conductor_de(1)
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id"] == 340
    assert cuerpo["estado"] == "ACEPTADO"
    assert cuerpo["respuesta"] == "ACEPTADO"
    assert cuerpo["hora_rta"] == HORA_RTA
    assert casos_solicitudes["responder"].llamadas == [
        {
            "id_solicitud": 340,
            "respuesta": EstadoSolicitud.ACEPTADO,
            "hora_rta": datetime(2026, 10, 3, 18, 44, 10, tzinfo=UTC),
            "identidad": Identidad(roles=frozenset({"conductor"}), id_conductor=1),
        }
    ]


def test_responder_pasa_la_identidad_del_operador(
    client_solicitudes, casos_solicitudes, headers_operador
) -> None:
    respuesta = client_solicitudes.post(
        RESPONDER.format(id=340),
        json={**CUERPO, "respuesta": "RECHAZADO"},
        headers=headers_operador,
    )

    assert respuesta.status_code == 200
    llamada = casos_solicitudes["responder"].llamadas[0]
    assert llamada["respuesta"] is EstadoSolicitud.RECHAZADO
    assert llamada["identidad"] == Identidad(roles=frozenset({"operador"}), id_operador=7)


@pytest.mark.parametrize(
    ("error", "status_code", "codigo"),
    [
        (NoEncontrado("No existe la solicitud 340"), 404, "NO_ENCONTRADO"),
        (AccesoProhibido("La solicitud es de otro conductor"), 403, "ACCESO_PROHIBIDO"),
        (SolicitudYaRespondida("Ya fue respondida"), 409, "SOLICITUD_YA_RESPONDIDA"),
        (SolicitudVencida("Ya venció"), 410, "SOLICITUD_VENCIDA"),
        (ConductorNoHabilitado("No está habilitado"), 422, "CONDUCTOR_NO_HABILITADO"),
    ],
    ids=["404", "403-ajena", "409", "410", "422"],
)
def test_responder_mapea_los_errores_del_caso_de_uso(
    client_solicitudes, casos_solicitudes, headers_conductor_de, error, status_code, codigo
) -> None:
    casos_solicitudes["responder"].error = error

    respuesta = client_solicitudes.post(
        RESPONDER.format(id=340), json=CUERPO, headers=headers_conductor_de(1)
    )

    assert respuesta.status_code == status_code
    assert respuesta.json()["codigo"] == codigo


def test_el_servicio_no_responde_solicitudes(
    client_solicitudes, casos_solicitudes, headers_servicio
) -> None:
    respuesta = client_solicitudes.post(
        RESPONDER.format(id=340), json=CUERPO, headers=headers_servicio
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "SIN_PERMISOS"
    assert casos_solicitudes["responder"].llamadas == []


@pytest.mark.parametrize(
    "cuerpo",
    [
        {},
        {"respuesta": "ACEPTADO"},
        {"hora_rta": HORA_RTA},
        {"respuesta": "PENDIENTE", "hora_rta": HORA_RTA},
        {"respuesta": "ACEPTADO", "hora_rta": "ayer"},
        {"respuesta": "ACEPTADO", "hora_rta": "2026-10-03T18:44:10"},
        {"respuesta": "ACEPTADO", "hora_rta": "2026-10-03"},
    ],
    ids=[
        "vacio",
        "sin-hora",
        "sin-respuesta",
        "respuesta-invalida",
        "hora-invalida",
        "hora-sin-zona",
        "solo-fecha",
    ],
)
def test_responder_con_cuerpo_invalido_es_400(
    client_solicitudes, casos_solicitudes, headers_conductor_de, cuerpo
) -> None:
    respuesta = client_solicitudes.post(
        RESPONDER.format(id=340), json=cuerpo, headers=headers_conductor_de(1)
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert casos_solicitudes["responder"].llamadas == []
