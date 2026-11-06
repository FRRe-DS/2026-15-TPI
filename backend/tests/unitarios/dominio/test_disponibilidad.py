"""Reglas del estado operativo del conductor (US2 y US5).

Firmas bajo prueba:
    puede_quedar_disponible(conductor, vehiculo_activo) -> bool
    aplicar_cambio_estado(conductor, vehiculo_activo, *, estado, id_vehiculo_activo, ahora)
        -> bool
    marcar_ocupado(conductor, vehiculo_activo, ahora) -> None

`aplicar_cambio_estado` distingue "no informado" de `None`: para el vehiculo activo,
no informarlo conserva el actual y `None` lo quita.
"""

from datetime import UTC, datetime

import pytest
from app.dominio.conductor import Conductor, EstadoConductor
from app.dominio.disponibilidad import (
    aplicar_cambio_estado,
    marcar_ocupado,
    puede_quedar_disponible,
)
from app.dominio.errores import ConductorNoHabilitado
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.vehiculo import TipoServicio, TipoVehiculo, Vehiculo

AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
ANTES = datetime(2026, 6, 15, 10, 0, tzinfo=UTC)
APROBADA = EstadoHabilitacion.APROBADA
PENDIENTE = EstadoHabilitacion.PENDIENTE
SUSPENDIDA = EstadoHabilitacion.SUSPENDIDA


def crear_conductor(
    *,
    estado=EstadoConductor.DESCONECTADO,
    habilitacion=APROBADA,
    id_vehiculo_activo=None,
    fecha_ultimo_cambio_estado=ANTES,
):
    return Conductor(
        dni="30123456",
        nombre="Ana",
        apellido="Perez",
        telefono="+54 379 4000000",
        email="ana@example.com",
        habilitacion=habilitacion,
        estado=estado,
        id_vehiculo_activo=id_vehiculo_activo,
        fecha_ultimo_cambio_estado=fecha_ultimo_cambio_estado,
        id=1,
    )


def crear_vehiculo(*, habilitacion=APROBADA, id_vehiculo=5):
    vehiculo = Vehiculo.crear(
        tipo=TipoVehiculo.AUTO,
        patente="AB123CD",
        marca="Toyota",
        modelo="Corolla",
        anio=2020,
        tipos_servicio=[TipoServicio.PASAJEROS],
    )
    vehiculo.habilitacion = habilitacion
    vehiculo.id = id_vehiculo
    vehiculo.id_conductor = 1
    return vehiculo


# --- puede_quedar_disponible ---


@pytest.mark.parametrize(
    ("habilitacion_conductor", "habilitacion_vehiculo", "esperado"),
    [
        (APROBADA, APROBADA, True),
        (PENDIENTE, APROBADA, False),
        (SUSPENDIDA, APROBADA, False),
        (APROBADA, PENDIENTE, False),
        (APROBADA, SUSPENDIDA, False),
    ],
    ids=[
        "ambos-aprobados",
        "conductor-pendiente",
        "conductor-suspendido",
        "vehiculo-pendiente",
        "vehiculo-suspendido",
    ],
)
def test_puede_quedar_disponible_solo_si_conductor_y_vehiculo_estan_aprobados(
    habilitacion_conductor, habilitacion_vehiculo, esperado
):
    conductor = crear_conductor(habilitacion=habilitacion_conductor)
    vehiculo = crear_vehiculo(habilitacion=habilitacion_vehiculo)

    assert puede_quedar_disponible(conductor, vehiculo) is esperado


def test_puede_quedar_disponible_requiere_un_vehiculo_activo():
    assert puede_quedar_disponible(crear_conductor(), None) is False


# --- aplicar_cambio_estado: pedir DISPONIBLE ---


@pytest.mark.parametrize(
    ("habilitacion_conductor", "habilitacion_vehiculo", "vehiculo"),
    [
        (PENDIENTE, APROBADA, "aprobado"),
        (SUSPENDIDA, APROBADA, "aprobado"),
        (APROBADA, PENDIENTE, "pendiente"),
        (APROBADA, SUSPENDIDA, "suspendido"),
        (APROBADA, APROBADA, None),
    ],
    ids=[
        "conductor-pendiente",
        "conductor-suspendido",
        "vehiculo-pendiente",
        "vehiculo-suspendido",
        "sin-vehiculo",
    ],
)
def test_pedir_disponible_sin_cumplir_la_regla_lanza_y_no_cambia_nada(
    habilitacion_conductor, habilitacion_vehiculo, vehiculo
):
    conductor = crear_conductor(
        estado=EstadoConductor.CONECTADO,
        habilitacion=habilitacion_conductor,
        id_vehiculo_activo=5,
    )
    vehiculo_activo = (
        None if vehiculo is None else crear_vehiculo(habilitacion=habilitacion_vehiculo)
    )
    id_vehiculo_activo = None if vehiculo is None else 5

    with pytest.raises(ConductorNoHabilitado):
        aplicar_cambio_estado(
            conductor,
            vehiculo_activo,
            estado=EstadoConductor.DISPONIBLE,
            id_vehiculo_activo=id_vehiculo_activo,
            ahora=AHORA,
        )

    assert conductor.estado is EstadoConductor.CONECTADO
    assert conductor.id_vehiculo_activo == 5
    assert conductor.fecha_ultimo_cambio_estado == ANTES


@pytest.mark.parametrize(
    "estado_inicial",
    [EstadoConductor.DESCONECTADO, EstadoConductor.CONECTADO, EstadoConductor.OCUPADO],
)
def test_pedir_disponible_cumpliendo_la_regla_lo_deja_disponible(estado_inicial):
    conductor = crear_conductor(estado=estado_inicial, id_vehiculo_activo=5)

    cambio = aplicar_cambio_estado(
        conductor,
        crear_vehiculo(),
        estado=EstadoConductor.DISPONIBLE,
        ahora=AHORA,
    )

    assert cambio is True
    assert conductor.estado is EstadoConductor.DISPONIBLE
    assert conductor.id_vehiculo_activo == 5
    assert conductor.fecha_ultimo_cambio_estado == AHORA


# --- aplicar_cambio_estado: DESCONECTADO y CONECTADO ---


@pytest.mark.parametrize("estado_inicial", list(EstadoConductor))
@pytest.mark.parametrize("estado_pedido", [EstadoConductor.DESCONECTADO, EstadoConductor.CONECTADO])
def test_pedir_desconectado_o_conectado_se_acepta_desde_cualquier_estado(
    estado_inicial, estado_pedido
):
    conductor = crear_conductor(estado=estado_inicial)

    cambio = aplicar_cambio_estado(
        conductor,
        None,
        estado=estado_pedido,
        ahora=AHORA,
    )

    assert cambio is (estado_pedido is not estado_inicial)
    assert conductor.estado is estado_pedido
    if estado_pedido is not estado_inicial:
        assert conductor.fecha_ultimo_cambio_estado == AHORA


# --- aplicar_cambio_estado: quitar o cambiar el vehiculo activo ---


@pytest.mark.parametrize(
    ("estado_inicial", "estado_esperado"),
    [
        (EstadoConductor.DISPONIBLE, EstadoConductor.CONECTADO),
        (EstadoConductor.CONECTADO, EstadoConductor.CONECTADO),
        (EstadoConductor.OCUPADO, EstadoConductor.OCUPADO),
    ],
)
def test_quitar_el_vehiculo_activo_solo_baja_a_conectado_si_estaba_disponible(
    estado_inicial, estado_esperado
):
    conductor = crear_conductor(estado=estado_inicial, id_vehiculo_activo=5)

    cambio = aplicar_cambio_estado(
        conductor,
        None,
        id_vehiculo_activo=None,
        ahora=AHORA,
    )

    assert cambio is True
    assert conductor.estado is estado_esperado
    assert conductor.id_vehiculo_activo is None
    assert conductor.fecha_ultimo_cambio_estado == AHORA


@pytest.mark.parametrize(
    ("estado_inicial", "estado_esperado"),
    [
        (EstadoConductor.DISPONIBLE, EstadoConductor.CONECTADO),
        (EstadoConductor.CONECTADO, EstadoConductor.CONECTADO),
        (EstadoConductor.OCUPADO, EstadoConductor.OCUPADO),
    ],
)
def test_cambiar_a_un_vehiculo_no_aprobado_solo_baja_a_conectado_si_estaba_disponible(
    estado_inicial, estado_esperado
):
    conductor = crear_conductor(estado=estado_inicial, id_vehiculo_activo=5)

    cambio = aplicar_cambio_estado(
        conductor,
        crear_vehiculo(habilitacion=PENDIENTE, id_vehiculo=6),
        id_vehiculo_activo=6,
        ahora=AHORA,
    )

    assert cambio is True
    assert conductor.estado is estado_esperado
    assert conductor.id_vehiculo_activo == 6
    assert conductor.fecha_ultimo_cambio_estado == AHORA


# --- aplicar_cambio_estado: fecha y "no informado" vs None ---


def test_un_pedido_que_no_cambia_nada_no_toca_la_fecha():
    conductor = crear_conductor(estado=EstadoConductor.CONECTADO, id_vehiculo_activo=5)

    cambio = aplicar_cambio_estado(
        conductor,
        crear_vehiculo(),
        estado=EstadoConductor.CONECTADO,
        id_vehiculo_activo=5,
        ahora=AHORA,
    )

    assert cambio is False
    assert conductor.estado is EstadoConductor.CONECTADO
    assert conductor.id_vehiculo_activo == 5
    assert conductor.fecha_ultimo_cambio_estado == ANTES


def test_vehiculo_no_informado_conserva_el_activo_y_la_fecha():
    conductor = crear_conductor(estado=EstadoConductor.CONECTADO, id_vehiculo_activo=5)

    cambio = aplicar_cambio_estado(
        conductor,
        crear_vehiculo(),
        estado=EstadoConductor.CONECTADO,
        ahora=AHORA,
    )

    assert cambio is False
    assert conductor.id_vehiculo_activo == 5
    assert conductor.fecha_ultimo_cambio_estado == ANTES


def test_vehiculo_nulo_explicito_quita_el_activo_y_actualiza_la_fecha():
    conductor = crear_conductor(estado=EstadoConductor.CONECTADO, id_vehiculo_activo=5)

    cambio = aplicar_cambio_estado(
        conductor,
        None,
        id_vehiculo_activo=None,
        ahora=AHORA,
    )

    assert cambio is True
    assert conductor.id_vehiculo_activo is None
    assert conductor.fecha_ultimo_cambio_estado == AHORA


def test_cambiar_solo_la_ubicacion_no_toca_la_fecha_del_estado():
    conductor = crear_conductor(estado=EstadoConductor.CONECTADO)

    conductor.fijar_ubicacion(-31.4, -64.2, AHORA)

    assert conductor.fecha_act_ubic == AHORA
    assert conductor.fecha_ultimo_cambio_estado == ANTES


# --- marcar_ocupado ---


@pytest.mark.parametrize("estado_inicial", [EstadoConductor.CONECTADO, EstadoConductor.DISPONIBLE])
def test_marcar_ocupado_deja_ocupado_y_actualiza_la_fecha(estado_inicial):
    conductor = crear_conductor(estado=estado_inicial, id_vehiculo_activo=5)

    marcar_ocupado(conductor, crear_vehiculo(), AHORA)

    assert conductor.estado is EstadoConductor.OCUPADO
    assert conductor.fecha_ultimo_cambio_estado == AHORA


@pytest.mark.parametrize("estado_inicial", [EstadoConductor.DESCONECTADO, EstadoConductor.OCUPADO])
def test_marcar_ocupado_lanza_si_el_estado_no_es_conectado_ni_disponible(estado_inicial):
    conductor = crear_conductor(estado=estado_inicial, id_vehiculo_activo=5)

    with pytest.raises(ConductorNoHabilitado):
        marcar_ocupado(conductor, crear_vehiculo(), AHORA)

    assert conductor.estado is estado_inicial
    assert conductor.fecha_ultimo_cambio_estado == ANTES


@pytest.mark.parametrize(
    ("habilitacion_conductor", "habilitacion_vehiculo", "con_vehiculo"),
    [
        (PENDIENTE, APROBADA, True),
        (SUSPENDIDA, APROBADA, True),
        (APROBADA, PENDIENTE, True),
        (APROBADA, SUSPENDIDA, True),
        (APROBADA, APROBADA, False),
    ],
    ids=[
        "conductor-pendiente",
        "conductor-suspendido",
        "vehiculo-pendiente",
        "vehiculo-suspendido",
        "sin-vehiculo",
    ],
)
def test_marcar_ocupado_lanza_si_no_cumple_la_regla_y_no_cambia_nada(
    habilitacion_conductor, habilitacion_vehiculo, con_vehiculo
):
    conductor = crear_conductor(
        estado=EstadoConductor.CONECTADO,
        habilitacion=habilitacion_conductor,
        id_vehiculo_activo=5 if con_vehiculo else None,
    )
    vehiculo = crear_vehiculo(habilitacion=habilitacion_vehiculo) if con_vehiculo else None

    with pytest.raises(ConductorNoHabilitado):
        marcar_ocupado(conductor, vehiculo, AHORA)

    assert conductor.estado is EstadoConductor.CONECTADO
    assert conductor.id_vehiculo_activo == (5 if con_vehiculo else None)
    assert conductor.fecha_ultimo_cambio_estado == ANTES
