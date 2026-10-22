from app.aplicacion.casos_de_uso.detalle_conductor import armar_detalle
from app.aplicacion.casos_de_uso.resultados import ConductorDetalle
from app.aplicacion.puertos.reloj import Reloj
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.vehiculo import TipoVehiculo


class ListarConductores:
    def __init__(self, uow: UnidadDeTrabajo, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    def ejecutar(
        self,
        *,
        habilitado: bool | None = None,
        disponible: bool | None = None,
        tipo_vehiculo: TipoVehiculo | None = None,
    ) -> list[ConductorDetalle]:
        with self._uow:
            conductores = self._uow.conductores.listar(
                habilitado=habilitado,
                disponible=disponible,
                tipo_vehiculo=tipo_vehiculo,
            )
            return [armar_detalle(self._uow, self._reloj, conductor) for conductor in conductores]
