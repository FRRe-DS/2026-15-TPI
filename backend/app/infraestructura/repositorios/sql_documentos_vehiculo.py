from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aplicacion.puertos.repositorio_documentos_vehiculo import (
    RepositorioDocumentosVehiculo,
)
from app.dominio.documento_vehiculo import DocumentoVehiculo, TipoDocumentoVehiculo
from app.infraestructura.db.modelos import VehiculoDocumento as DocumentoVehiculoOrm
from app.infraestructura.repositorios._sesion_sql import flush_aislado


def a_dominio(fila: DocumentoVehiculoOrm) -> DocumentoVehiculo:
    return DocumentoVehiculo(
        tipo=TipoDocumentoVehiculo(fila.tipo),
        numero=fila.numero,
        entidad_emisora=fila.entidad_emisora,
        fecha_emision=fila.fecha_emision,
        fecha_vencimiento=fila.fecha_vencimiento,
        url_archivo=fila.url_archivo,
        id=fila.id_documento,
    )


def _copiar_a_fila(
    id_vehiculo: int, documento: DocumentoVehiculo, fila: DocumentoVehiculoOrm
) -> None:
    fila.id_vehiculo = id_vehiculo
    fila.tipo = documento.tipo.value
    fila.numero = documento.numero
    fila.entidad_emisora = documento.entidad_emisora
    fila.fecha_emision = documento.fecha_emision
    fila.fecha_vencimiento = documento.fecha_vencimiento
    fila.url_archivo = documento.url_archivo


class SqlRepositorioDocumentosVehiculo(RepositorioDocumentosVehiculo):
    """Solo hace flush: confirmar o revertir es trabajo de la unidad de trabajo."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def guardar(self, id_vehiculo: int, documento: DocumentoVehiculo) -> DocumentoVehiculo:
        fila = DocumentoVehiculoOrm()
        _copiar_a_fila(id_vehiculo, documento, fila)
        flush_aislado(self._sesion, fila)
        documento.id = fila.id_documento
        return documento

    def listar_por_vehiculo(self, id_vehiculo: int) -> list[DocumentoVehiculo]:
        consulta = (
            select(DocumentoVehiculoOrm)
            .where(DocumentoVehiculoOrm.id_vehiculo == id_vehiculo)
            .order_by(DocumentoVehiculoOrm.id_documento)
        )
        return [a_dominio(fila) for fila in self._sesion.scalars(consulta)]

    def listar_por_vehiculos(
        self, ids_vehiculo: Sequence[int]
    ) -> dict[int, list[DocumentoVehiculo]]:
        por_vehiculo: dict[int, list[DocumentoVehiculo]] = {id_: [] for id_ in ids_vehiculo}
        if not por_vehiculo:
            return por_vehiculo
        consulta = (
            select(DocumentoVehiculoOrm)
            .where(DocumentoVehiculoOrm.id_vehiculo.in_(list(por_vehiculo)))
            .order_by(DocumentoVehiculoOrm.id_documento)
        )
        for fila in self._sesion.scalars(consulta):
            por_vehiculo[fila.id_vehiculo].append(a_dominio(fila))
        return por_vehiculo
