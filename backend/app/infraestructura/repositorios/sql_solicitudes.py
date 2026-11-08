from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aplicacion.puertos.repositorio_solicitudes import RepositorioSolicitudes
from app.dominio.errores import NoEncontrado
from app.dominio.solicitud import EstadoSolicitud, Solicitud
from app.infraestructura.db.modelos import Solicitud as SolicitudOrm
from app.infraestructura.repositorios._sesion_sql import flush_aislado


def a_dominio(fila: SolicitudOrm) -> Solicitud:
    respuesta = fila.respuesta
    return Solicitud(
        id_conductor=fila.id_conductor,
        vence_en=fila.vence_en,
        id_viaje=fila.id_viaje,
        estado=EstadoSolicitud(fila.estado),
        respuesta=None if respuesta is None else EstadoSolicitud(respuesta),
        hora_rta=fila.hora_rta,
        id=fila.id_solicitud,
    )


def _copiar_a_fila(solicitud: Solicitud, fila: SolicitudOrm) -> None:
    fila.id_conductor = solicitud.id_conductor
    fila.id_viaje = solicitud.id_viaje
    fila.estado = solicitud.estado.value
    fila.vence_en = solicitud.vence_en
    fila.respuesta = None if solicitud.respuesta is None else solicitud.respuesta.value
    fila.hora_rta = solicitud.hora_rta


class SqlRepositorioSolicitudes(RepositorioSolicitudes):
    """Solo hace flush: confirmar o revertir es trabajo de la unidad de trabajo."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def guardar(self, solicitud: Solicitud) -> Solicitud:
        fila = self._fila_a_guardar(solicitud)
        _copiar_a_fila(solicitud, fila)
        flush_aislado(self._sesion, fila)
        solicitud.id = fila.id_solicitud
        return solicitud

    def obtener(self, id_solicitud: int) -> Solicitud | None:
        fila = self._sesion.get(SolicitudOrm, id_solicitud)
        return None if fila is None else a_dominio(fila)

    def listar_por_conductor(self, id_conductor: int) -> list[Solicitud]:
        consulta = (
            select(SolicitudOrm)
            .where(SolicitudOrm.id_conductor == id_conductor)
            .order_by(SolicitudOrm.id_solicitud)
        )
        return [a_dominio(fila) for fila in self._sesion.scalars(consulta)]

    def _fila_a_guardar(self, solicitud: Solicitud) -> SolicitudOrm:
        if solicitud.id is None:
            return SolicitudOrm()
        fila = self._sesion.get(SolicitudOrm, solicitud.id)
        if fila is None:
            # Un id que no existe en la base no es un alta: se informa en vez de crearlo.
            raise NoEncontrado(f"No existe la solicitud {solicitud.id}")
        return fila
