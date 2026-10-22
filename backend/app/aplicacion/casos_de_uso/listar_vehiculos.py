from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.errores import NoEncontrado
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.vehiculo import TipoVehiculo, Vehiculo


class ListarVehiculos:
    def __init__(self, uow: UnidadDeTrabajo) -> None:
        self._uow = uow

    def ejecutar(
        self,
        *,
        id_conductor: int,
        tipo: TipoVehiculo | None = None,
        habilitacion: EstadoHabilitacion | None = None,
    ) -> list[Vehiculo]:
        with self._uow:
            if self._uow.conductores.obtener(id_conductor) is None:
                raise NoEncontrado(f"No existe el conductor {id_conductor}")
            return self._uow.vehiculos.listar_por_conductor(
                id_conductor, tipo=tipo, habilitacion=habilitacion
            )
