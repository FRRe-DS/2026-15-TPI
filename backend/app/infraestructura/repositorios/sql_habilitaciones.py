from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aplicacion.puertos.repositorio_habilitaciones import RepositorioHabilitaciones
from app.dominio.habilitacion import (
    AccionHabilitacion,
    EstadoHabilitacion,
    EventoHabilitacion,
)
from app.infraestructura.db.modelos import HabilitacionEventoConductor as EventoConductorOrm
from app.infraestructura.db.modelos import HabilitacionEventoVehiculo as EventoVehiculoOrm
from app.infraestructura.repositorios._sesion_sql import flush_aislado

EventoOrm = EventoConductorOrm | EventoVehiculoOrm


def _a_dominio(fila: EventoOrm) -> EventoHabilitacion:
    estado_anterior = fila.estado_anterior
    return EventoHabilitacion(
        id=fila.id_evento,
        accion=AccionHabilitacion(fila.accion),
        estado_anterior=None if estado_anterior is None else EstadoHabilitacion(estado_anterior),
        estado_nuevo=EstadoHabilitacion(fila.estado_nuevo),
        motivo=fila.motivo,
        id_operador=fila.id_operador,
        fecha=fila.fecha.astimezone(UTC),  # el driver la devuelve en la zona de la sesion
    )


def _copiar_a_fila(evento: EventoHabilitacion, fila: EventoOrm) -> None:
    fila.accion = evento.accion.value
    fila.estado_anterior = None if evento.estado_anterior is None else evento.estado_anterior.value
    fila.estado_nuevo = evento.estado_nuevo.value
    fila.motivo = evento.motivo
    fila.id_operador = evento.id_operador
    fila.fecha = evento.fecha


class SqlRepositorioHabilitaciones(RepositorioHabilitaciones):
    """Los eventos son de solo escritura. Solo hace flush, nunca commit."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def registrar_evento_conductor(self, id_conductor: int, evento: EventoHabilitacion) -> None:
        fila = EventoConductorOrm(id_conductor=id_conductor)
        _copiar_a_fila(evento, fila)
        flush_aislado(self._sesion, fila)

    def registrar_evento_vehiculo(self, id_vehiculo: int, evento: EventoHabilitacion) -> None:
        fila = EventoVehiculoOrm(id_vehiculo=id_vehiculo)
        _copiar_a_fila(evento, fila)
        flush_aislado(self._sesion, fila)

    def historial_conductor(self, id_conductor: int) -> list[EventoHabilitacion]:
        consulta = (
            select(EventoConductorOrm)
            .where(EventoConductorOrm.id_conductor == id_conductor)
            .order_by(EventoConductorOrm.id_evento)
        )
        return [_a_dominio(fila) for fila in self._sesion.scalars(consulta)]

    def historial_vehiculo(self, id_vehiculo: int) -> list[EventoHabilitacion]:
        consulta = (
            select(EventoVehiculoOrm)
            .where(EventoVehiculoOrm.id_vehiculo == id_vehiculo)
            .order_by(EventoVehiculoOrm.id_evento)
        )
        return [_a_dominio(fila) for fila in self._sesion.scalars(consulta)]
