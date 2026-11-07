from app.aplicacion.casos_de_uso.encontrado import exigir_conductor
from app.aplicacion.casos_de_uso.resultados import UbicacionDelConductor
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo


class ObtenerUbicacionConductor:
    def __init__(self, uow: UnidadDeTrabajo) -> None:
        self._uow = uow

    def ejecutar(self, *, id_conductor: int) -> UbicacionDelConductor:
        with self._uow:
            conductor = exigir_conductor(self._uow.conductores.obtener(id_conductor), id_conductor)
            return UbicacionDelConductor(
                id_conductor=conductor.id,
                latitud=conductor.latitud,
                longitud=conductor.longitud,
                fecha_act_ubic=conductor.fecha_act_ubic,
            )
