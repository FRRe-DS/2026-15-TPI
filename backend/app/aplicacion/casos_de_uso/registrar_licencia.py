from datetime import date

from app.aplicacion.casos_de_uso.resultados import DocumentoDeConductor
from app.aplicacion.puertos.reloj import Reloj
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.documento import Documento, TipoDocumento
from app.dominio.errores import NoEncontrado


class RegistrarLicencia:
    def __init__(self, uow: UnidadDeTrabajo, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    def ejecutar(
        self,
        *,
        id_conductor: int,
        numero: str,
        categoria: str | None,
        fecha_emision: date,
        fecha_vencimiento: date,
        url_archivo: str,
    ) -> DocumentoDeConductor:
        with self._uow:
            if self._uow.conductores.obtener(id_conductor) is None:
                raise NoEncontrado(f"No existe el conductor {id_conductor}")
            documento = Documento.crear(
                tipo=TipoDocumento.LICENCIA,
                numero=numero,
                categoria=categoria,
                fecha_emision=fecha_emision,
                fecha_vencimiento=fecha_vencimiento,
                url_archivo=url_archivo,
            )
            documento = self._uow.documentos.guardar(id_conductor, documento)
            self._uow.commit()
            return DocumentoDeConductor(
                id_conductor=id_conductor,
                documento=documento,
                estado=documento.estado_al(self._reloj.hoy()),
            )
