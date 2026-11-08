"""Esquemas de las solicitudes de viaje (operaciones 16 y 17)."""

from datetime import datetime
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel

from app.dominio.solicitud import Solicitud as SolicitudDominio


class EstadoSolicitud(StrEnum):
    PENDIENTE = "PENDIENTE"
    ACEPTADO = "ACEPTADO"
    RECHAZADO = "RECHAZADO"
    VENCIDA = "VENCIDA"


class RespuestaSolicitud(StrEnum):
    """Lo único que el conductor puede responder: `PENDIENTE` y `VENCIDA` no se piden."""

    ACEPTADO = "ACEPTADO"
    RECHAZADO = "RECHAZADO"


class RespuestaSolicitudRequest(BaseModel):
    respuesta: RespuestaSolicitud
    # Con zona horaria: se guarda tal cual en una columna `timestamptz`.
    hora_rta: AwareDatetime


class Solicitud(BaseModel):
    id: int
    id_conductor: int
    id_viaje: int | None = None
    estado: EstadoSolicitud
    vence_en: datetime
    respuesta: RespuestaSolicitud | None = None
    hora_rta: datetime | None = None


def solicitud_desde_dominio(solicitud: SolicitudDominio) -> Solicitud:
    assert solicitud.id is not None
    return Solicitud(
        id=solicitud.id,
        id_conductor=solicitud.id_conductor,
        id_viaje=solicitud.id_viaje,
        estado=EstadoSolicitud(solicitud.estado.value),
        vence_en=solicitud.vence_en,
        respuesta=(
            RespuestaSolicitud(solicitud.respuesta.value)
            if solicitud.respuesta is not None
            else None
        ),
        hora_rta=solicitud.hora_rta,
    )
