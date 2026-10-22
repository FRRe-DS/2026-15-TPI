from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aplicacion.puertos.repositorio_documentos import RepositorioDocumentos
from app.dominio.documento import Documento, TipoDocumento
from app.infraestructura.db.modelos import DocumentoConductor as DocumentoOrm
from app.infraestructura.repositorios._sesion_sql import flush_aislado


def _a_dominio(fila: DocumentoOrm) -> Documento:
    return Documento(
        tipo=TipoDocumento(fila.tipo),
        numero=fila.numero,
        categoria=fila.categoria,
        fecha_emision=fila.fecha_emision,
        fecha_vencimiento=fila.fecha_vencimiento,
        url_archivo=fila.url_archivo,
        id=fila.id_documento,
    )


def _copiar_a_fila(id_conductor: int, documento: Documento, fila: DocumentoOrm) -> None:
    fila.id_conductor = id_conductor
    fila.tipo = documento.tipo.value
    fila.numero = documento.numero
    fila.categoria = documento.categoria
    fila.fecha_emision = documento.fecha_emision
    fila.fecha_vencimiento = documento.fecha_vencimiento
    fila.url_archivo = documento.url_archivo


class SqlRepositorioDocumentos(RepositorioDocumentos):
    """Solo hace flush: confirmar o revertir es trabajo de la unidad de trabajo."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def guardar(self, id_conductor: int, documento: Documento) -> Documento:
        fila = DocumentoOrm()
        _copiar_a_fila(id_conductor, documento, fila)
        flush_aislado(self._sesion, fila)
        documento.id = fila.id_documento
        return documento

    def listar_por_conductor(self, id_conductor: int) -> list[Documento]:
        # Consulta explicita: la relacion del ORM ordena por vencimiento, no por alta.
        consulta = (
            select(DocumentoOrm)
            .where(DocumentoOrm.id_conductor == id_conductor)
            .order_by(DocumentoOrm.id_documento)
        )
        return [_a_dominio(fila) for fila in self._sesion.scalars(consulta)]
