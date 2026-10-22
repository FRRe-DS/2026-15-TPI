from app.aplicacion.casos_de_uso.encontrado import exigir_encontrado
from app.aplicacion.casos_de_uso.historial import en_orden_cronologico
from app.aplicacion.casos_de_uso.resultados import HabilitacionVehiculoEventos
from app.aplicacion.puertos.reloj import Reloj
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.habilitacion import AccionHabilitacion, aplicar_accion


class AccionarHabilitacionVehiculo:
    def __init__(self, uow: UnidadDeTrabajo, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    def ejecutar(
        self,
        *,
        id_conductor: int,
        id_vehiculo: int,
        accion: AccionHabilitacion,
        motivo: str,
        id_operador: int,
    ) -> HabilitacionVehiculoEventos:
        with self._uow:
            vehiculo = exigir_encontrado(
                self._uow.bloquear_vehiculo(id_conductor, id_vehiculo),
                f"el vehiculo {id_vehiculo} del conductor {id_conductor}",
            )
            evento = aplicar_accion(
                vehiculo.habilitacion,
                accion,
                motivo,
                id_operador,
                self._reloj.ahora(),
            )
            vehiculo.habilitacion = evento.estado_nuevo
            self._uow.vehiculos.guardar(vehiculo)
            self._uow.habilitaciones.registrar_evento_vehiculo(id_vehiculo, evento)
            self._uow.commit()
            historial = self._uow.habilitaciones.historial_vehiculo(id_vehiculo)
            return HabilitacionVehiculoEventos(
                id_vehiculo=id_vehiculo,
                estado=vehiculo.habilitacion,
                eventos=en_orden_cronologico(historial),
            )
