from dataclasses import replace

from app.aplicacion.casos_de_uso.encontrado import exigir_conductor
from app.aplicacion.puertos.reloj import Reloj
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.solicitud import EstadoSolicitud, Solicitud


class ListarSolicitudesConductor:
    def __init__(self, uow: UnidadDeTrabajo, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    def ejecutar(
        self,
        *,
        id_conductor: int,
        estado: EstadoSolicitud | None = None,
    ) -> list[Solicitud]:
        """Devuelve copias con el estado efectivo; las solicitudes guardadas no cambian."""
        with self._uow:
            exigir_conductor(self._uow.conductores.obtener(id_conductor), id_conductor)
            ahora = self._reloj.ahora()
            solicitudes = [
                replace(solicitud, estado=solicitud.estado_efectivo(ahora))
                for solicitud in self._uow.solicitudes.listar_por_conductor(id_conductor)
            ]
        if estado is None:
            return solicitudes
        return [solicitud for solicitud in solicitudes if solicitud.estado is estado]
