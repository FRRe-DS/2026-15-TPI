from datetime import datetime

from app.dominio.habilitacion import (
    AccionHabilitacion,
    EstadoHabilitacion,
    EventoHabilitacion,
)


def en_orden_cronologico(eventos: list[EventoHabilitacion]) -> list[EventoHabilitacion]:
    # sorted es estable: ante fechas iguales se mantiene el orden de registro.
    return sorted(eventos, key=lambda evento: evento.fecha)


def evento_de_alta(motivo: str, fecha: datetime) -> EventoHabilitacion:
    return EventoHabilitacion(
        accion=AccionHabilitacion.ALTA,
        estado_anterior=None,
        estado_nuevo=EstadoHabilitacion.PENDIENTE,
        motivo=motivo,
        id_operador=None,
        fecha=fecha,
    )
