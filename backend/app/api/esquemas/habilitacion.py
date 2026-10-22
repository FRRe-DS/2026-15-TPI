from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.aplicacion.casos_de_uso.resultados import (
    HabilitacionEventos as HabilitacionEventosDominio,
)
from app.aplicacion.casos_de_uso.resultados import (
    HabilitacionResumen as HabilitacionResumenDominio,
)
from app.aplicacion.casos_de_uso.resultados import (
    HabilitacionVehiculoEventos as HabilitacionVehiculoEventosDominio,
)
from app.dominio.habilitacion import EventoHabilitacion


class EstadoHabilitacion(StrEnum):
    PENDIENTE = "PENDIENTE"
    OBSERVADA = "OBSERVADA"
    APROBADA = "APROBADA"
    SUSPENDIDA = "SUSPENDIDA"
    RECHAZADA = "RECHAZADA"


class AccionHabilitacion(StrEnum):
    ALTA = "ALTA"
    APROBAR = "APROBAR"
    OBSERVAR = "OBSERVAR"
    SUSPENDER = "SUSPENDER"
    RECHAZAR = "RECHAZAR"


class AccionSolicitada(StrEnum):
    APROBAR = "APROBAR"
    OBSERVAR = "OBSERVAR"
    SUSPENDER = "SUSPENDER"
    RECHAZAR = "RECHAZAR"


class HabilitacionAccionRequest(BaseModel):
    accion: AccionSolicitada
    motivo: str = Field(min_length=1, max_length=500)


class HabilitacionHistorialItem(BaseModel):
    estado: EstadoHabilitacion
    motivo: str = Field(max_length=500)
    id_operador: int | None = None
    fecha: datetime


class HabilitacionResumen(BaseModel):
    id_conductor: int
    estado: EstadoHabilitacion
    historial: list[HabilitacionHistorialItem]


class HabilitacionEvento(BaseModel):
    # El dominio todavía no expone el id del evento (deuda de S1).
    id: int | None = None
    accion: AccionHabilitacion
    estado_anterior: EstadoHabilitacion | None = None
    estado_nuevo: EstadoHabilitacion
    motivo: str = Field(max_length=500)
    id_operador: int | None = None
    fecha: datetime


class HabilitacionEventos(BaseModel):
    id_conductor: int
    estado: EstadoHabilitacion
    eventos: list[HabilitacionEvento]


class HabilitacionVehiculoEventos(BaseModel):
    id_vehiculo: int
    estado: EstadoHabilitacion
    eventos: list[HabilitacionEvento]


def _evento(evento: EventoHabilitacion) -> HabilitacionEvento:
    return HabilitacionEvento(
        accion=AccionHabilitacion(evento.accion.value),
        estado_anterior=(
            EstadoHabilitacion(evento.estado_anterior.value)
            if evento.estado_anterior is not None
            else None
        ),
        estado_nuevo=EstadoHabilitacion(evento.estado_nuevo.value),
        motivo=evento.motivo,
        id_operador=evento.id_operador,
        fecha=evento.fecha,
    )


def resumen_desde_dominio(
    resumen: HabilitacionResumenDominio,
) -> HabilitacionResumen:
    return HabilitacionResumen(
        id_conductor=resumen.id_conductor,
        estado=EstadoHabilitacion(resumen.estado.value),
        historial=[
            HabilitacionHistorialItem(
                estado=EstadoHabilitacion(item.estado_nuevo.value),
                motivo=item.motivo,
                id_operador=item.id_operador,
                fecha=item.fecha,
            )
            for item in resumen.historial
        ],
    )


def eventos_conductor_desde_dominio(
    resultado: HabilitacionEventosDominio,
) -> HabilitacionEventos:
    return HabilitacionEventos(
        id_conductor=resultado.id_conductor,
        estado=EstadoHabilitacion(resultado.estado.value),
        eventos=[_evento(evento) for evento in resultado.eventos],
    )


def eventos_vehiculo_desde_dominio(
    resultado: HabilitacionVehiculoEventosDominio,
) -> HabilitacionVehiculoEventos:
    return HabilitacionVehiculoEventos(
        id_vehiculo=resultado.id_vehiculo,
        estado=EstadoHabilitacion(resultado.estado.value),
        eventos=[_evento(evento) for evento in resultado.eventos],
    )
