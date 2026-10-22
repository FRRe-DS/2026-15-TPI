from types import TracebackType
from typing import Self

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.conductor import Conductor
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
