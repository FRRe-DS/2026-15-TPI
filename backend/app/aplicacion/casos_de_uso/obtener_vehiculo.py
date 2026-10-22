from app.aplicacion.casos_de_uso.encontrado import exigir_vehiculo
from app.aplicacion.casos_de_uso.resultados import VehiculoDetalle
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo


class ObtenerVehiculo:
    def __init__(self, uow: UnidadDeTrabajo) -> None:
        self._uow = uow

    def ejecutar(self, *, id_conductor: int, id_vehiculo: int) -> VehiculoDetalle:
        with self._uow:
            vehiculo = exigir_vehiculo(
                self._uow.vehiculos.obtener(id_conductor, id_vehiculo), id_conductor, id_vehiculo
            )
            return VehiculoDetalle(vehiculo=vehiculo)
