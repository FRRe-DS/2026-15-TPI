"""Matriz de transiciones de habilitacion (compartida por conductor y vehiculo).

Firma bajo prueba:
    aplicar_accion(estado_actual, accion, motivo, id_operador, fecha) -> evento
El evento expone: accion, estado_anterior, estado_nuevo, motivo, id_operador, fecha.
"""

import itertools
from datetime import UTC, datetime

import pytest

from app.dominio.errores import DatosInvalidos, TransicionInvalida
from app.dominio.habilitacion import (
    AccionHabilitacion,
    EstadoHabilitacion,
    aplicar_accion,
)

PENDIENTE = EstadoHabilitacion.PENDIENTE
OBSERVADA = EstadoHabilitacion.OBSERVADA
APROBADA = EstadoHabilitacion.APROBADA
SUSPENDIDA = EstadoHabilitacion.SUSPENDIDA
RECHAZADA = EstadoHabilitacion.RECHAZADA

APROBAR = AccionHabilitacion.APROBAR
OBSERVAR = AccionHabilitacion.OBSERVAR
SUSPENDER = AccionHabilitacion.SUSPENDER
RECHAZAR = AccionHabilitacion.RECHAZAR

TRANSICIONES_VALIDAS = {
    (PENDIENTE, APROBAR): APROBADA,
    (PENDIENTE, OBSERVAR): OBSERVADA,
    (PENDIENTE, RECHAZAR): RECHAZADA,
    (OBSERVADA, APROBAR): APROBADA,
    (OBSERVADA, RECHAZAR): RECHAZADA,
    (APROBADA, SUSPENDER): SUSPENDIDA,
    (SUSPENDIDA, APROBAR): APROBADA,
    (SUSPENDIDA, RECHAZAR): RECHAZADA,
}

TRANSICIONES_NO_PERMITIDAS = [
    combinacion
    for combinacion in itertools.product(EstadoHabilitacion, AccionHabilitacion)
    if combinacion not in TRANSICIONES_VALIDAS
]

ID_OPERADOR = 7
FECHA = datetime(2026, 3, 15, 10, 30, tzinfo=UTC)
MOTIVO = "Documentacion revisada"


@pytest.mark.parametrize(
    ("estado_actual", "accion", "estado_esperado"),
    [
        (estado, accion, nuevo)
        for (estado, accion), nuevo in TRANSICIONES_VALIDAS.items()
    ],
    ids=lambda valor: valor.name,
)
def test_aplica_las_transiciones_de_la_matriz(estado_actual, accion, estado_esperado):
    evento = aplicar_accion(
        estado_actual=estado_actual,
        accion=accion,
        motivo=MOTIVO,
        id_operador=ID_OPERADOR,
        fecha=FECHA,
    )

    assert evento.estado_nuevo is estado_esperado


def test_el_evento_registra_estado_anterior_estado_nuevo_motivo_operador_y_fecha():
    evento = aplicar_accion(
        estado_actual=PENDIENTE,
        accion=APROBAR,
        motivo=MOTIVO,
        id_operador=ID_OPERADOR,
        fecha=FECHA,
    )

    assert evento.accion is APROBAR
    assert evento.estado_anterior is PENDIENTE
    assert evento.estado_nuevo is APROBADA
    assert evento.motivo == MOTIVO
    assert evento.id_operador == ID_OPERADOR
    assert evento.fecha == FECHA


@pytest.mark.parametrize(
    ("estado_actual", "accion"),
    TRANSICIONES_NO_PERMITIDAS,
    ids=lambda valor: valor.name,
)
def test_rechaza_las_transiciones_fuera_de_la_matriz(estado_actual, accion):
    with pytest.raises(TransicionInvalida):
        aplicar_accion(
            estado_actual=estado_actual,
            accion=accion,
            motivo=MOTIVO,
            id_operador=ID_OPERADOR,
            fecha=FECHA,
        )


@pytest.mark.parametrize("motivo", ["", "   ", "\t\n"])
def test_rechaza_motivo_vacio_o_solo_espacios(motivo):
    with pytest.raises(DatosInvalidos):
        aplicar_accion(
            estado_actual=PENDIENTE,
            accion=APROBAR,
            motivo=motivo,
            id_operador=ID_OPERADOR,
            fecha=FECHA,
        )
