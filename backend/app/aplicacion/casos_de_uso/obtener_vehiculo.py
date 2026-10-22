from app.aplicacion.casos_de_uso.resultados import VehiculoDetalle
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.errores import NoEncontrado


class ObtenerVehiculo:
    def __init__(self, uow: UnidadDeTrabajo) -> None:
        self._uow = uow

    def ejecutar(self, *, id_conductor: int, id_vehiculo: int) -> VehiculoDetalle:
        with self._uow:
            vehiculo = self._uow.vehiculos.obtener(id_conductor, id_vehiculo)
            if vehiculo is None:
                raise NoEncontrado(
                    f"No existe el vehiculo {id_vehiculo} del conductor {id_conductor}"
                )
            return VehiculoDetalle(vehiculo=vehiculo)
