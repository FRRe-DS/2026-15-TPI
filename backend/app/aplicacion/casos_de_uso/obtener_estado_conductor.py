from app.aplicacion.casos_de_uso.encontrado import exigir_conductor
from app.aplicacion.casos_de_uso.resultados import EstadoDelConductor
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo


class ObtenerEstadoConductor:
    def __init__(self, uow: UnidadDeTrabajo) -> None:
        self._uow = uow

    def ejecutar(self, *, id_conductor: int) -> EstadoDelConductor:
        with self._uow:
            conductor = exigir_conductor(self._uow.conductores.obtener(id_conductor), id_conductor)
            return EstadoDelConductor.desde_conductor(conductor)
