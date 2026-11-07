from datetime import date

from app.aplicacion.casos_de_uso.encontrado import exigir_vehiculo
from app.aplicacion.casos_de_uso.resultados import DocumentoVehiculoConEstado, VehiculoDetalle
from app.aplicacion.puertos.reloj import Reloj
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.documento_vehiculo import DocumentoVehiculo


def _con_estado(documentos: list[DocumentoVehiculo], hoy: date) -> list[DocumentoVehiculoConEstado]:
    return [DocumentoVehiculoConEstado(doc, doc.estado_al(hoy)) for doc in documentos]


class ObtenerVehiculo:
    def __init__(self, uow: UnidadDeTrabajo, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    def ejecutar(self, *, id_conductor: int, id_vehiculo: int) -> VehiculoDetalle:
        with self._uow:
            vehiculo = exigir_vehiculo(
                self._uow.vehiculos.obtener(id_conductor, id_vehiculo), id_conductor, id_vehiculo
            )
            documentos = self._uow.documentos_vehiculo.listar_por_vehiculo(id_vehiculo)
            return VehiculoDetalle(
                vehiculo=vehiculo,
                documentos=_con_estado(documentos, self._reloj.hoy()),
            )
