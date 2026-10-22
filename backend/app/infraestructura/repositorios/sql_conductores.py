from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.aplicacion.puertos.repositorio_conductores import RepositorioConductores
from app.dominio.conductor import Conductor
from app.dominio.errores import DniDuplicado, NoEncontrado
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.vehiculo import TipoVehiculo
from app.infraestructura.db.modelos import Conductor as ConductorOrm
from app.infraestructura.db.modelos import Vehiculo as VehiculoOrm
from app.infraestructura.repositorios._errores_sql import nombre_de_restriccion
from app.infraestructura.repositorios._sesion_sql import flush_aislado

RESTRICCION_DNI_UNICO = "uq_conductor_dni"


def a_dominio(fila: ConductorOrm) -> Conductor:
    return Conductor(
        dni=fila.dni,
        nombre=fila.nombre,
        apellido=fila.apellido,
        telefono=fila.telefono,
        email=fila.email,
        habilitacion=EstadoHabilitacion(fila.estado_habilitacion),
        conectado=fila.conectado,
        disponible=fila.disponible,
        id=fila.id_conductor,
    )


def _copiar_a_fila(conductor: Conductor, fila: ConductorOrm) -> None:
    fila.dni = conductor.dni
    fila.nombre = conductor.nombre
    fila.apellido = conductor.apellido
    fila.telefono = conductor.telefono
    fila.email = conductor.email
    fila.estado_habilitacion = conductor.habilitacion.value
    fila.conectado = conductor.conectado
    fila.disponible = conductor.disponible


class SqlRepositorioConductores(RepositorioConductores):
    """Solo hace flush: confirmar o revertir es trabajo de la unidad de trabajo."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def guardar(self, conductor: Conductor) -> Conductor:
        fila = self._fila_a_guardar(conductor)
        _copiar_a_fila(conductor, fila)
        self._guardar_traduciendo_duplicado(fila)
        conductor.id = fila.id_conductor
        return conductor

    def obtener(self, id_conductor: int) -> Conductor | None:
        fila = self._sesion.get(ConductorOrm, id_conductor)
        return None if fila is None else a_dominio(fila)

    def listar(
        self,
        *,
        habilitado: bool | None = None,
        disponible: bool | None = None,
        tipo_vehiculo: TipoVehiculo | None = None,
    ) -> list[Conductor]:
        consulta = select(ConductorOrm).order_by(ConductorOrm.id_conductor)
        if habilitado is True:
            consulta = consulta.where(ConductorOrm.estado_habilitacion == "APROBADA")
        elif habilitado is False:
            consulta = consulta.where(ConductorOrm.estado_habilitacion != "APROBADA")
        if disponible is not None:
            consulta = consulta.where(ConductorOrm.disponible == disponible)
        if tipo_vehiculo is not None:
            consulta = consulta.where(
                ConductorOrm.vehiculos.any(VehiculoOrm.tipo == tipo_vehiculo.value)
            )
        return [a_dominio(fila) for fila in self._sesion.scalars(consulta)]

    def _fila_a_guardar(self, conductor: Conductor) -> ConductorOrm:
        if conductor.id is None:
            return ConductorOrm()
        fila = self._sesion.get(ConductorOrm, conductor.id)
        if fila is None:
            # Un id que no existe en la base no es un alta: se informa en vez de crearlo.
            raise NoEncontrado(f"No existe el conductor {conductor.id}")
        return fila

    def _guardar_traduciendo_duplicado(self, fila: ConductorOrm) -> None:
        """Flush aislado que traduce la violacion de unicidad a error de dominio."""
        try:
            flush_aislado(self._sesion, fila)
        except IntegrityError as error:
            if nombre_de_restriccion(error) == RESTRICCION_DNI_UNICO:
                raise DniDuplicado("Ya existe un conductor con ese DNI") from error
            raise
