from datetime import date

from app.aplicacion.casos_de_uso.encontrado import exigir_vehiculo
from app.aplicacion.casos_de_uso.resultados import DocumentoDeVehiculo
from app.aplicacion.puertos.reloj import Reloj
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.documento_vehiculo import DocumentoVehiculo, TipoDocumentoVehiculo


class RegistrarDocumentoVehiculo:
    def __init__(self, uow: UnidadDeTrabajo, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    def ejecutar(
        self,
        *,
        id_conductor: int,
        id_vehiculo: int,
        tipo: TipoDocumentoVehiculo,
        numero: str,
        entidad_emisora: str | None,
        fecha_emision: date,
        fecha_vencimiento: date,
        url_archivo: str,
    ) -> DocumentoDeVehiculo:
        with self._uow:
            exigir_vehiculo(
                self._uow.vehiculos.obtener(id_conductor, id_vehiculo), id_conductor, id_vehiculo
            )
            documento = DocumentoVehiculo.crear(
                tipo=tipo,
                numero=numero,
                entidad_emisora=entidad_emisora,
                fecha_emision=fecha_emision,
                fecha_vencimiento=fecha_vencimiento,
                url_archivo=url_archivo,
            )
            documento = self._uow.documentos_vehiculo.guardar(id_vehiculo, documento)
            self._uow.commit()
            return DocumentoDeVehiculo(
                id_vehiculo=id_vehiculo,
                documento=documento,
                estado=documento.estado_al(self._reloj.hoy()),
            )
