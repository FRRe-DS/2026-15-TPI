from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.dominio.errores import DatosInvalidos, TransicionInvalida


class EstadoHabilitacion(Enum):
    PENDIENTE = "PENDIENTE"
    OBSERVADA = "OBSERVADA"
    APROBADA = "APROBADA"
    SUSPENDIDA = "SUSPENDIDA"
    RECHAZADA = "RECHAZADA"


class AccionHabilitacion(Enum):
    ALTA = "ALTA"
    APROBAR = "APROBAR"
    OBSERVAR = "OBSERVAR"
    SUSPENDER = "SUSPENDER"
    RECHAZAR = "RECHAZAR"


_E = EstadoHabilitacion
_A = AccionHabilitacion

TRANSICIONES: dict[_E, dict[_A, _E]] = {
    _E.PENDIENTE: {
        _A.APROBAR: _E.APROBADA,
        _A.OBSERVAR: _E.OBSERVADA,
        _A.RECHAZAR: _E.RECHAZADA,
    },
    _E.OBSERVADA: {_A.APROBAR: _E.APROBADA, _A.RECHAZAR: _E.RECHAZADA},
    _E.APROBADA: {_A.SUSPENDER: _E.SUSPENDIDA},
    _E.SUSPENDIDA: {_A.APROBAR: _E.APROBADA, _A.RECHAZAR: _E.RECHAZADA},
    _E.RECHAZADA: {},
}


@dataclass(frozen=True)
class EventoHabilitacion:
    accion: AccionHabilitacion
    estado_anterior: EstadoHabilitacion
    estado_nuevo: EstadoHabilitacion
    motivo: str
    id_operador: int
    fecha: datetime


def aplicar_accion(
    estado_actual: EstadoHabilitacion,
    accion: AccionHabilitacion,
    motivo: str,
    id_operador: int,
    fecha: datetime,
) -> EventoHabilitacion:
    estado_nuevo = TRANSICIONES[estado_actual].get(accion)
    if estado_nuevo is None:
        raise TransicionInvalida(
            f"La acción {accion.value} no está permitida desde {estado_actual.value}"
        )
    if not motivo.strip():
        raise DatosInvalidos("El motivo es obligatorio")
    return EventoHabilitacion(
        accion=accion,
        estado_anterior=estado_actual,
        estado_nuevo=estado_nuevo,
        motivo=motivo,
        id_operador=id_operador,
        fecha=fecha,
    )
