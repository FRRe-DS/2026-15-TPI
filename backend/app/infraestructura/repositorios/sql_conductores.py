from sqlalchemy import ColumnElement, and_, false, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.aplicacion.puertos.repositorio_conductores import RepositorioConductores
from app.dominio.conductor import Conductor, EstadoConductor
from app.dominio.errores import DniDuplicado, NoEncontrado
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.vehiculo import TipoServicio, TipoVehiculo
from app.infraestructura.db.modelos import Conductor as ConductorOrm
from app.infraestructura.db.modelos import Vehiculo as VehiculoOrm
from app.infraestructura.repositorios._errores_sql import nombre_de_restriccion
from app.infraestructura.repositorios._sesion_sql import flush_aislado

RESTRICCION_DNI_UNICO = "uq_conductor_dni"
ESTADO_APROBADA = EstadoHabilitacion.APROBADA.value


# TRANSITORIO hasta L9 (migracion 0002): la base no tiene `estado`, `id_vehiculo_activo`,
# `fecha_ultimo_cambio_estado` ni los totales de puntaje. `OCUPADO` se guarda como `CONECTADO`
# y esos campos no se persisten.
def _estado_desde_booleanos(conectado: bool, disponible: bool) -> EstadoConductor:
    """Adaptacion transitoria: la base todavia no tiene la columna `estado`."""
    if not conectado:
        return EstadoConductor.DESCONECTADO
    if disponible:
        return EstadoConductor.DISPONIBLE
    return EstadoConductor.CONECTADO


def _booleanos_desde_estado(estado: EstadoConductor) -> tuple[bool, bool]:
    """Adaptacion transitoria: `OCUPADO` no se distingue de `CONECTADO` en la base."""
    if estado is EstadoConductor.DESCONECTADO:
        return False, False
    if estado is EstadoConductor.DISPONIBLE:
        return True, True
    return True, False


def _condicion_de_estado(estado: EstadoConductor) -> ColumnElement[bool]:
    """Traduce `estado` a las columnas actuales, de modo que coincida con lo que lee `a_dominio`.

    TRANSITORIO hasta L9: `OCUPADO` no existe en la base (se guarda y se lee como `CONECTADO`),
    asi que filtrar por `OCUPADO` no devuelve ningun conductor.
    """
    if estado is EstadoConductor.DESCONECTADO:
        return ConductorOrm.conectado.is_(False)
    if estado is EstadoConductor.DISPONIBLE:
        return and_(ConductorOrm.conectado.is_(True), ConductorOrm.disponible.is_(True))
    if estado is EstadoConductor.CONECTADO:
        return and_(ConductorOrm.conectado.is_(True), ConductorOrm.disponible.is_(False))
    return false()


def a_dominio(fila: ConductorOrm) -> Conductor:
    return Conductor(
        dni=fila.dni,
        nombre=fila.nombre,
        apellido=fila.apellido,
        telefono=fila.telefono,
        email=fila.email,
        habilitacion=EstadoHabilitacion(fila.estado_habilitacion),
        estado=_estado_desde_booleanos(fila.conectado, fila.disponible),
        id=fila.id_conductor,
        latitud=fila.latitud,
        longitud=fila.longitud,
        fecha_act_ubic=fila.fecha_act_ubic,
        fecha_alta=fila.fecha_alta,
    )


def _copiar_a_fila(conductor: Conductor, fila: ConductorOrm) -> None:
    fila.dni = conductor.dni
    fila.nombre = conductor.nombre
    fila.apellido = conductor.apellido
    fila.telefono = conductor.telefono
    fila.email = conductor.email
    fila.estado_habilitacion = conductor.habilitacion.value
    fila.conectado, fila.disponible = _booleanos_desde_estado(conductor.estado)


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
        estado: EstadoConductor | None = None,
        tipo_vehiculo: TipoVehiculo | None = None,
        tipo_servicio: TipoServicio | None = None,
    ) -> list[Conductor]:
        if tipo_servicio is not None:
            # TRANSITORIO hasta L9: `vehiculo_tipo_servicio` llega con la migracion 0002.
            raise NotImplementedError("El filtro por tipo de servicio llega con L9")
        consulta = select(ConductorOrm).order_by(ConductorOrm.id_conductor)
        if habilitado is True:
            consulta = consulta.where(ConductorOrm.estado_habilitacion == ESTADO_APROBADA)
        elif habilitado is False:
            consulta = consulta.where(ConductorOrm.estado_habilitacion != ESTADO_APROBADA)
        if estado is not None:
            consulta = consulta.where(_condicion_de_estado(estado))
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
