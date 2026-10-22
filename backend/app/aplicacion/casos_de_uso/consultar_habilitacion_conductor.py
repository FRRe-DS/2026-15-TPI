from app.aplicacion.casos_de_uso.resultados import HabilitacionResumen
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.errores import NoEncontrado


class ConsultarHabilitacionConductor:
    def __init__(self, uow: UnidadDeTrabajo) -> None:
        self._uow = uow

    def ejecutar(self, *, id_conductor: int) -> HabilitacionResumen:
        with self._uow:
            conductor = self._uow.conductores.obtener(id_conductor)
            if conductor is None:
                raise NoEncontrado(f"No existe el conductor {id_conductor}")
            historial = self._uow.habilitaciones.historial_conductor(id_conductor)
            return HabilitacionResumen(
                id_conductor=id_conductor,
                estado=conductor.habilitacion,
                historial=sorted(historial, key=lambda evento: evento.fecha),
            )
