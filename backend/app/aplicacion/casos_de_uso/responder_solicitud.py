from datetime import datetime

from app.aplicacion.casos_de_uso.encontrado import exigir_conductor, exigir_solicitud
from app.aplicacion.politicas.acceso import (
    ROLES_ESCRITURA_CONDUCTOR,
    Identidad,
    verificar_acceso,
)
from app.aplicacion.puertos.reloj import Reloj
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.conductor import Conductor
from app.dominio.disponibilidad import marcar_ocupado
from app.dominio.solicitud import EstadoSolicitud, Solicitud
from app.dominio.vehiculo import Vehiculo

ROLES_RESPONDER_SOLICITUD = ROLES_ESCRITURA_CONDUCTOR


class ResponderSolicitud:
    def __init__(self, uow: UnidadDeTrabajo, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    def ejecutar(
        self,
        *,
        id_solicitud: int,
        respuesta: EstadoSolicitud,
        hora_rta: datetime,
        identidad: Identidad,
    ) -> Solicitud:
        with self._uow:
            solicitud_sin_bloquear = exigir_solicitud(
                self._uow.solicitudes.obtener(id_solicitud), id_solicitud
            )
            id_conductor = solicitud_sin_bloquear.id_conductor
            verificar_acceso(identidad, id_conductor, ROLES_RESPONDER_SOLICITUD)

            # Orden fijo de bloqueos (conductor y despues solicitud) para no cruzarse con
            # el cambio de estado del mismo conductor. La solicitud se relee ya bloqueada
            # porque otra respuesta pudo ganarnos de mano entre la lectura y el bloqueo.
            conductor = exigir_conductor(self._uow.bloquear_conductor(id_conductor), id_conductor)
            solicitud = exigir_solicitud(self._uow.bloquear_solicitud(id_solicitud), id_solicitud)

            ahora = self._reloj.ahora()
            solicitud.responder(respuesta, hora_rta, ahora)
            if respuesta is EstadoSolicitud.ACEPTADO:
                self._dejar_ocupado(conductor, ahora)

            self._uow.solicitudes.guardar(solicitud)
            self._uow.commit()
            return solicitud

    def _dejar_ocupado(self, conductor: Conductor, ahora: datetime) -> None:
        marcar_ocupado(conductor, self._buscar_vehiculo_activo(conductor), ahora)
        self._uow.conductores.guardar(conductor)

    def _buscar_vehiculo_activo(self, conductor: Conductor) -> Vehiculo | None:
        if conductor.id_vehiculo_activo is None:
            return None
        return self._uow.vehiculos.obtener(conductor.id, conductor.id_vehiculo_activo)
