from app.aplicacion.casos_de_uso.detalle_conductor import armar_detalles
from app.aplicacion.casos_de_uso.resultados import ConductorDetalle
from app.aplicacion.puertos.reloj import Reloj
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.conductor import EstadoConductor
from app.dominio.vehiculo import TipoServicio, TipoVehiculo


class ListarConductores:
    def __init__(self, uow: UnidadDeTrabajo, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    def ejecutar(
        self,
        *,
        habilitado: bool | None = None,
        estado: EstadoConductor | None = None,
        tipo_vehiculo: TipoVehiculo | None = None,
        tipo_servicio: TipoServicio | None = None,
    ) -> list[ConductorDetalle]:
        with self._uow:
            conductores = self._uow.conductores.listar(
                habilitado=habilitado,
                estado=estado,
                tipo_vehiculo=tipo_vehiculo,
                tipo_servicio=tipo_servicio,
            )
            return armar_detalles(self._uow, self._reloj, conductores)
