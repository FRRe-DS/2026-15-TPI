from app.aplicacion.casos_de_uso.encontrado import exigir_encontrado
from app.aplicacion.casos_de_uso.historial import en_orden_cronologico
from app.aplicacion.casos_de_uso.resultados import HabilitacionResumen
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo


class ConsultarHabilitacionConductor:
    def __init__(self, uow: UnidadDeTrabajo) -> None:
        self._uow = uow

    def ejecutar(self, *, id_conductor: int) -> HabilitacionResumen:
        with self._uow:
            conductor = exigir_encontrado(
                self._uow.conductores.obtener(id_conductor),
                f"el conductor {id_conductor}",
            )
            historial = self._uow.habilitaciones.historial_conductor(id_conductor)
            return HabilitacionResumen(
                id_conductor=id_conductor,
                estado=conductor.habilitacion,
                historial=en_orden_cronologico(historial),
            )
