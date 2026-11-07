from app.aplicacion.casos_de_uso.encontrado import exigir_vehiculo
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.vehiculo import ServicioDelVehiculo


class ListarTiposServicioVehiculo:
    def __init__(self, uow: UnidadDeTrabajo) -> None:
        self._uow = uow

    def ejecutar(self, *, id_conductor: int, id_vehiculo: int) -> list[ServicioDelVehiculo]:
        with self._uow:
            vehiculo = exigir_vehiculo(
                self._uow.vehiculos.obtener(id_conductor, id_vehiculo), id_conductor, id_vehiculo
            )
            return list(vehiculo.tipos_servicio)
