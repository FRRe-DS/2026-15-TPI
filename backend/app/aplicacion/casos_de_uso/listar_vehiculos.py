from app.aplicacion.casos_de_uso.encontrado import exigir_conductor
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
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
            exigir_conductor(self._uow.conductores.obtener(id_conductor), id_conductor)
            return self._uow.vehiculos.listar_por_conductor(
                id_conductor, tipo=tipo, habilitacion=habilitacion
            )
