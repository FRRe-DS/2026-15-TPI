from app.aplicacion.casos_de_uso.encontrado import exigir_encontrado
from app.aplicacion.casos_de_uso.historial import evento_de_alta
from app.aplicacion.casos_de_uso.resultados import VehiculoDetalle
from app.aplicacion.puertos.reloj import Reloj
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.vehiculo import TipoServicio, TipoVehiculo, Vehiculo

MOTIVO_ALTA = "Alta del vehiculo"


class RegistrarVehiculo:
    def __init__(self, uow: UnidadDeTrabajo, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    def ejecutar(
        self,
        *,
        id_conductor: int,
        tipo: TipoVehiculo,
        patente: str,
        marca: str,
        modelo: str,
        anio: int,
        tipos_servicio: list[TipoServicio],
    ) -> VehiculoDetalle:
        with self._uow:
            exigir_encontrado(
                self._uow.conductores.obtener(id_conductor),
                f"el conductor {id_conductor}",
            )
            vehiculo = Vehiculo.crear(
                tipo=tipo,
                patente=patente,
                marca=marca,
                modelo=modelo,
                anio=anio,
                tipos_servicio=tipos_servicio,
            )
            vehiculo.id_conductor = id_conductor
            vehiculo = self._uow.vehiculos.guardar(vehiculo)
            self._uow.habilitaciones.registrar_evento_vehiculo(
                vehiculo.id, evento_de_alta(MOTIVO_ALTA, self._reloj.ahora())
            )
            self._uow.commit()
            return VehiculoDetalle(vehiculo=vehiculo)
