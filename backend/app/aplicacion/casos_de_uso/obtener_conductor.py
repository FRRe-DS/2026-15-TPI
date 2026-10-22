from app.aplicacion.casos_de_uso.detalle_conductor import armar_detalle
from app.aplicacion.casos_de_uso.encontrado import exigir_conductor
from app.aplicacion.casos_de_uso.resultados import ConductorDetalle
from app.aplicacion.puertos.reloj import Reloj
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo


class ObtenerConductor:
    def __init__(self, uow: UnidadDeTrabajo, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    def ejecutar(self, *, id_conductor: int) -> ConductorDetalle:
        with self._uow:
            conductor = exigir_conductor(self._uow.conductores.obtener(id_conductor), id_conductor)
            return armar_detalle(self._uow, self._reloj, conductor)
