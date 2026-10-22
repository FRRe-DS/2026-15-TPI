from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import AnyUrl, BaseModel, Field

from app.dominio.documento import Documento as DocumentoDominio
from app.dominio.documento import EstadoDocumento as EstadoDocumentoDominio


class EstadoDocumento(StrEnum):
    VIGENTE = "VIGENTE"
    VENCIDO = "VENCIDO"


class DocumentoConductorCreate(BaseModel):
    tipo: Literal["LICENCIA"] = "LICENCIA"
    numero: str = Field(min_length=1, max_length=50)
    categoria: str | None = Field(default=None, max_length=10)
    fecha_emision: date
    fecha_vencimiento: date
    url_archivo: AnyUrl = Field(max_length=500)


class DocumentoConductor(DocumentoConductorCreate):
    id_conductor: int
    estado: EstadoDocumento


def documento_desde_dominio(
    id_conductor: int,
    documento: DocumentoDominio,
    estado: EstadoDocumentoDominio,
) -> DocumentoConductor:
    return DocumentoConductor(
        tipo=documento.tipo.value,
        numero=documento.numero,
        categoria=documento.categoria,
        fecha_emision=documento.fecha_emision,
        fecha_vencimiento=documento.fecha_vencimiento,
        url_archivo=str(documento.url_archivo),
        id_conductor=id_conductor,
        estado=EstadoDocumento(estado.value),
    )
