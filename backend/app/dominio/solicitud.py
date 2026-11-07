"""Solicitud de viaje ofrecida a un conductor (US5).

Una solicitud `PENDIENTE` vence cuando la hora del servidor supera `vence_en`. El estado
`VENCIDA` no se escribe al leer: se calcula con `estado_efectivo`; el estado guardado solo
cambia cuando el conductor acepta o rechaza dentro del plazo.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.dominio.errores import SolicitudVencida, SolicitudYaRespondida


class EstadoSolicitud(Enum):
    PENDIENTE = "PENDIENTE"
    ACEPTADO = "ACEPTADO"
    RECHAZADO = "RECHAZADO"
    VENCIDA = "VENCIDA"


@dataclass
class Solicitud:
    id_conductor: int
    vence_en: datetime
    id_viaje: int | None = None
    estado: EstadoSolicitud = EstadoSolicitud.PENDIENTE
    respuesta: EstadoSolicitud | None = None
    hora_rta: datetime | None = None
    id: int | None = None

    def estado_efectivo(self, ahora: datetime) -> EstadoSolicitud:
        if self.estado is EstadoSolicitud.PENDIENTE and ahora > self.vence_en:
            return EstadoSolicitud.VENCIDA
        return self.estado

    def responder(
        self,
        respuesta: EstadoSolicitud,
        hora_rta: datetime,
        ahora: datetime,
    ) -> None:
        """Registra la respuesta de una solicitud pendiente y vigente.

        `ahora` es la hora del servidor y decide el vencimiento; `hora_rta` es la hora que
        envio el cliente y se guarda tal cual.
        """
        estado_actual = self.estado_efectivo(ahora)
        if estado_actual is EstadoSolicitud.VENCIDA:
            raise SolicitudVencida("La solicitud ya venció")
        if estado_actual is not EstadoSolicitud.PENDIENTE:
            raise SolicitudYaRespondida("La solicitud ya fue respondida")

        self.estado = respuesta
        self.respuesta = respuesta
        self.hora_rta = hora_rta
