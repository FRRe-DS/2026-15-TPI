from collections.abc import Sequence
from types import TracebackType
from typing import Self

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.aplicacion.puertos.repositorio_documentos_vehiculo import (
    RepositorioDocumentosVehiculo,
)
from app.aplicacion.puertos.repositorio_solicitudes import RepositorioSolicitudes
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.conductor import Conductor
from app.dominio.documento_vehiculo import DocumentoVehiculo
from app.dominio.solicitud import Solicitud
from app.dominio.vehiculo import Vehiculo
from app.infraestructura.db.modelos import Conductor as ConductorOrm
from app.infraestructura.db.modelos import Vehiculo as VehiculoOrm
from app.infraestructura.repositorios.sql_conductores import (
    SqlRepositorioConductores,
)
from app.infraestructura.repositorios.sql_conductores import (
    a_dominio as conductor_a_dominio,
)
from app.infraestructura.repositorios.sql_documentos import SqlRepositorioDocumentos
from app.infraestructura.repositorios.sql_habilitaciones import (
    SqlRepositorioHabilitaciones,
)
from app.infraestructura.repositorios.sql_vehiculos import SqlRepositorioVehiculos
from app.infraestructura.repositorios.sql_vehiculos import (
    a_dominio as vehiculo_a_dominio,
)


def _pendiente(que: str) -> NotImplementedError:
    return NotImplementedError(f"{que} todavía no tiene implementación SQL")


class _SqlRepositorioSolicitudesPendiente(RepositorioSolicitudes):
    """Marcador hasta que exista la implementación SQL: falla al usarse, no al arrancar."""

    def guardar(self, solicitud: Solicitud) -> Solicitud:
        raise _pendiente("El repositorio de solicitudes")

    def obtener(self, id_solicitud: int) -> Solicitud | None:
        raise _pendiente("El repositorio de solicitudes")

    def listar_por_conductor(self, id_conductor: int) -> list[Solicitud]:
        raise _pendiente("El repositorio de solicitudes")


class _SqlRepositorioDocumentosVehiculoPendiente(RepositorioDocumentosVehiculo):
    """Marcador hasta que exista la implementación SQL: falla al usarse, no al arrancar."""

    def guardar(self, id_vehiculo: int, documento: DocumentoVehiculo) -> DocumentoVehiculo:
        raise _pendiente("El repositorio de documentos del vehículo")

    def listar_por_vehiculo(self, id_vehiculo: int) -> list[DocumentoVehiculo]:
        raise _pendiente("El repositorio de documentos del vehículo")

    def listar_por_vehiculos(
        self, ids_vehiculo: Sequence[int]
    ) -> dict[int, list[DocumentoVehiculo]]:
        raise _pendiente("El repositorio de documentos del vehículo")


class SqlUnidadDeTrabajo(UnidadDeTrabajo):
    """Una transaccion por `with`: abre una Session nueva y la cierra al salir."""

    def __init__(self, fabrica_sesiones: sessionmaker[Session]) -> None:
        self._fabrica_sesiones = fabrica_sesiones

    def __enter__(self) -> Self:
        self._sesion = self._fabrica_sesiones()
        self.conductores = SqlRepositorioConductores(self._sesion)
        self.vehiculos = SqlRepositorioVehiculos(self._sesion)
        self.documentos = SqlRepositorioDocumentos(self._sesion)
        self.habilitaciones = SqlRepositorioHabilitaciones(self._sesion)
        self.solicitudes = _SqlRepositorioSolicitudesPendiente()
        self.documentos_vehiculo = _SqlRepositorioDocumentosVehiculoPendiente()
        return self

    def __exit__(
        self,
        tipo_excepcion: type[BaseException] | None,
        excepcion: BaseException | None,
        traza: TracebackType | None,
    ) -> None:
        self._sesion.rollback()
        self._sesion.close()

    def commit(self) -> None:
        self._sesion.commit()

    def rollback(self) -> None:
        self._sesion.rollback()

    def bloquear_conductor(self, id_conductor: int) -> Conductor | None:
        consulta = (
            select(ConductorOrm).where(ConductorOrm.id_conductor == id_conductor).with_for_update()
        )
        fila = self._sesion.scalars(consulta).first()
        return None if fila is None else conductor_a_dominio(fila)

    def bloquear_vehiculo(self, id_conductor: int, id_vehiculo: int) -> Vehiculo | None:
        consulta = (
            select(VehiculoOrm)
            .where(
                VehiculoOrm.id_vehiculo == id_vehiculo,
                VehiculoOrm.id_conductor == id_conductor,
            )
            .options(selectinload(VehiculoOrm.tipos_servicio))
            .with_for_update()
        )
        fila = self._sesion.scalars(consulta).first()
        return None if fila is None else vehiculo_a_dominio(fila)

    def bloquear_solicitud(self, id_solicitud: int) -> Solicitud | None:
        raise _pendiente("El bloqueo de solicitudes")
