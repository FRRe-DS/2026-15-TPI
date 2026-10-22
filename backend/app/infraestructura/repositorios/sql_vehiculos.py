from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.aplicacion.puertos.repositorio_vehiculos import RepositorioVehiculos
from app.dominio.errores import NoEncontrado, PatenteDuplicada
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.vehiculo import (
    ServicioDelVehiculo,
    TipoServicio,
    TipoVehiculo,
    Vehiculo,
)
from app.infraestructura.db.modelos import Vehiculo as VehiculoOrm
from app.infraestructura.db.modelos import VehiculoTipoServicio as ServicioOrm
from app.infraestructura.repositorios._errores_sql import nombre_de_restriccion
from app.infraestructura.repositorios._sesion_sql import flush_aislado

RESTRICCION_PATENTE_UNICA = "uq_vehiculo_patente"


def a_dominio(fila: VehiculoOrm) -> Vehiculo:
    return Vehiculo(
        tipo=TipoVehiculo(fila.tipo),
        patente=fila.patente,
        marca=fila.marca,
        modelo=fila.modelo,
        anio=fila.anio,
        tipos_servicio=[
            ServicioDelVehiculo(TipoServicio(servicio.tipo_servicio), servicio.habilitado)
            for servicio in fila.tipos_servicio
        ],
        habilitacion=EstadoHabilitacion(fila.estado_habilitacion),
        id=fila.id_vehiculo,
        id_conductor=fila.id_conductor,
    )


def _copiar_a_fila(vehiculo: Vehiculo, fila: VehiculoOrm) -> None:
    fila.id_conductor = vehiculo.id_conductor
    fila.tipo = vehiculo.tipo.value
    fila.patente = vehiculo.patente
    fila.marca = vehiculo.marca
    fila.modelo = vehiculo.modelo
    fila.anio = vehiculo.anio
    fila.estado_habilitacion = vehiculo.habilitacion.value
    _sincronizar_servicios(vehiculo.tipos_servicio, fila)


def _sincronizar_servicios(servicios: list[ServicioDelVehiculo], fila: VehiculoOrm) -> None:
    """Actualiza, agrega y quita los servicios por tipo, sin recrear los existentes."""
    habilitado_por_tipo = {servicio.tipo.value: servicio.habilitado for servicio in servicios}
    existentes = {hijo.tipo_servicio: hijo for hijo in fila.tipos_servicio}
    for tipo, hijo in existentes.items():
        if tipo not in habilitado_por_tipo:
            fila.tipos_servicio.remove(hijo)
    for tipo, habilitado in habilitado_por_tipo.items():
        if tipo in existentes:
            existentes[tipo].habilitado = habilitado
        else:
            fila.tipos_servicio.append(ServicioOrm(tipo_servicio=tipo, habilitado=habilitado))


class SqlRepositorioVehiculos(RepositorioVehiculos):
    """Solo hace flush: confirmar o revertir es trabajo de la unidad de trabajo."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def guardar(self, vehiculo: Vehiculo) -> Vehiculo:
        fila = self._fila_a_guardar(vehiculo)
        _copiar_a_fila(vehiculo, fila)
        self._guardar_traduciendo_duplicado(fila)
        vehiculo.id = fila.id_vehiculo
        return vehiculo

    def obtener(self, id_conductor: int, id_vehiculo: int) -> Vehiculo | None:
        consulta = select(VehiculoOrm).where(
            VehiculoOrm.id_vehiculo == id_vehiculo,
            VehiculoOrm.id_conductor == id_conductor,
        )
        fila = self._sesion.scalars(consulta).first()
        return None if fila is None else a_dominio(fila)

    def listar_por_conductor(
        self,
        id_conductor: int,
        *,
        tipo: TipoVehiculo | None = None,
        habilitacion: EstadoHabilitacion | None = None,
    ) -> list[Vehiculo]:
        consulta = (
            select(VehiculoOrm)
            .where(VehiculoOrm.id_conductor == id_conductor)
            .order_by(VehiculoOrm.id_vehiculo)
        )
        if tipo is not None:
            consulta = consulta.where(VehiculoOrm.tipo == tipo.value)
        if habilitacion is not None:
            consulta = consulta.where(VehiculoOrm.estado_habilitacion == habilitacion.value)
        return [a_dominio(fila) for fila in self._sesion.scalars(consulta)]

    def _fila_a_guardar(self, vehiculo: Vehiculo) -> VehiculoOrm:
        if vehiculo.id is None:
            return VehiculoOrm()
        fila = self._sesion.get(VehiculoOrm, vehiculo.id)
        if fila is None:
            # Un id que no existe en la base no es un alta: se informa en vez de crearlo.
            raise NoEncontrado(f"No existe el vehiculo {vehiculo.id}")
        return fila

    def _guardar_traduciendo_duplicado(self, fila: VehiculoOrm) -> None:
        """Flush aislado que traduce la violacion de unicidad a error de dominio."""
        try:
            flush_aislado(self._sesion, fila)
        except IntegrityError as error:
            if nombre_de_restriccion(error) == RESTRICCION_PATENTE_UNICA:
                raise PatenteDuplicada("Ya existe un vehiculo con esa patente") from error
            raise
