"""Solicitud de viaje (US5).

Firmas bajo prueba:
    Solicitud(id_conductor, vence_en, id_viaje=None, estado=PENDIENTE, ...)
    solicitud.estado_efectivo(ahora) -> EstadoSolicitud
    solicitud.responder(respuesta, hora_rta, ahora) -> None

`PENDIENTE` vence cuando `ahora > vence_en` (la igualdad sigue vigente). Los demas
estados no cambian. La hora que decide el vencimiento es `ahora` (hora del servidor),
no la `hora_rta` que envia el cliente, que se guarda tal cual.
"""

from datetime import UTC, datetime, timedelta

import pytest
from app.dominio.errores import DatosInvalidos, SolicitudVencida, SolicitudYaRespondida
from app.dominio.solicitud import EstadoSolicitud, Solicitud

AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
VENCE_EN = AHORA + timedelta(minutes=5)
DESPUES_DEL_VENCIMIENTO = VENCE_EN + timedelta(seconds=1)
ANTES_DEL_VENCIMIENTO = VENCE_EN - timedelta(seconds=1)


def crear(**cambios):
    datos = {"id_conductor": 1, "vence_en": VENCE_EN}
    datos.update(cambios)
    return Solicitud(**datos)


def test_enum_de_estados_de_solicitud():
    assert [estado.value for estado in EstadoSolicitud] == [
        "PENDIENTE",
        "ACEPTADO",
        "RECHAZADO",
        "VENCIDA",
    ]


def test_solicitud_nueva_queda_pendiente_y_sin_respuesta():
    solicitud = crear()

    assert solicitud.estado is EstadoSolicitud.PENDIENTE
    assert solicitud.respuesta is None
    assert solicitud.hora_rta is None


@pytest.mark.parametrize(
    ("ahora", "estado_esperado"),
    [
        (ANTES_DEL_VENCIMIENTO, EstadoSolicitud.PENDIENTE),
        (VENCE_EN, EstadoSolicitud.PENDIENTE),
        (DESPUES_DEL_VENCIMIENTO, EstadoSolicitud.VENCIDA),
    ],
    ids=["antes", "justo-en-el-limite", "despues"],
)
def test_estado_efectivo_de_una_pendiente_depende_de_ahora(ahora, estado_esperado):
    assert crear().estado_efectivo(ahora) is estado_esperado


@pytest.mark.parametrize(
    "estado_guardado",
    [EstadoSolicitud.ACEPTADO, EstadoSolicitud.RECHAZADO, EstadoSolicitud.VENCIDA],
)
def test_estado_efectivo_no_cambia_los_estados_ya_definidos(estado_guardado):
    solicitud = crear(estado=estado_guardado)

    assert solicitud.estado_efectivo(DESPUES_DEL_VENCIMIENTO) is estado_guardado


@pytest.mark.parametrize("respuesta", [EstadoSolicitud.ACEPTADO, EstadoSolicitud.RECHAZADO])
def test_responder_una_pendiente_vigente_guarda_la_respuesta_tal_cual(respuesta):
    solicitud = crear()
    hora_rta = AHORA

    solicitud.responder(respuesta, hora_rta, AHORA)

    assert solicitud.estado is respuesta
    assert solicitud.respuesta is respuesta
    assert solicitud.hora_rta == hora_rta


def test_una_pendiente_vencida_lanza_y_no_cambia_nada():
    solicitud = crear()

    with pytest.raises(SolicitudVencida):
        solicitud.responder(
            EstadoSolicitud.ACEPTADO, ANTES_DEL_VENCIMIENTO, DESPUES_DEL_VENCIMIENTO
        )

    assert solicitud.estado is EstadoSolicitud.PENDIENTE
    assert solicitud.respuesta is None
    assert solicitud.hora_rta is None


def test_una_pendiente_vigente_con_hora_rta_posterior_al_vencimiento_se_acepta():
    solicitud = crear()

    solicitud.responder(EstadoSolicitud.RECHAZADO, DESPUES_DEL_VENCIMIENTO, ANTES_DEL_VENCIMIENTO)

    assert solicitud.estado is EstadoSolicitud.RECHAZADO
    assert solicitud.hora_rta == DESPUES_DEL_VENCIMIENTO


@pytest.mark.parametrize("estado_guardado", [EstadoSolicitud.ACEPTADO, EstadoSolicitud.RECHAZADO])
def test_una_solicitud_ya_respondida_lanza_y_no_cambia_nada(estado_guardado):
    solicitud = crear(
        estado=estado_guardado,
        respuesta=estado_guardado,
        hora_rta=ANTES_DEL_VENCIMIENTO,
    )

    with pytest.raises(SolicitudYaRespondida):
        solicitud.responder(EstadoSolicitud.RECHAZADO, AHORA, AHORA)

    assert solicitud.estado is estado_guardado
    assert solicitud.respuesta is estado_guardado
    assert solicitud.hora_rta == ANTES_DEL_VENCIMIENTO


def test_una_solicitud_guardada_como_vencida_lanza_vencida():
    solicitud = crear(estado=EstadoSolicitud.VENCIDA)

    with pytest.raises(SolicitudVencida):
        solicitud.responder(EstadoSolicitud.ACEPTADO, AHORA, AHORA)

    assert solicitud.estado is EstadoSolicitud.VENCIDA
    assert solicitud.respuesta is None
    assert solicitud.hora_rta is None


@pytest.mark.parametrize("respuesta", [EstadoSolicitud.PENDIENTE, EstadoSolicitud.VENCIDA])
def test_responder_solo_admite_aceptado_o_rechazado(respuesta):
    solicitud = crear()

    with pytest.raises(DatosInvalidos):
        solicitud.responder(respuesta, ANTES_DEL_VENCIMIENTO, AHORA)

    assert solicitud.estado is EstadoSolicitud.PENDIENTE
    assert solicitud.respuesta is None
    assert solicitud.hora_rta is None
