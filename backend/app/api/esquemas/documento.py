from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import AnyUrl, BaseModel, Field, HttpUrl

from app.dominio.documento import Documento as DocumentoDominio
from app.dominio.documento import EstadoDocumento as EstadoDocumentoDominio
from app.dominio.documento_vehiculo import DocumentoVehiculo as DocumentoVehiculoDominio


class EstadoDocumento(StrEnum):
    VIGENTE = "VIGENTE"
    VENCIDO = "VENCIDO"


class DocumentoConductorCreate(BaseModel):
    tipo: Literal["LICENCIA"] = "LICENCIA"
    numero: str = Field(min_length=1, max_length=50)
    categoria: str | None = Field(default=None, max_length=10)
    fecha_emision: date
    fecha_vencimiento: date
    url_archivo: HttpUrl = Field(max_length=500)


class DocumentoConductor(DocumentoConductorCreate):
    # Solo la entrada exige http o https: un documento guardado antes con otro
    # esquema no debe romper las lecturas.
    url_archivo: AnyUrl = Field(max_length=500)
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


class TipoDocumentoVehiculo(StrEnum):
    SEGURO = "SEGURO"
    CEDULA_VERDE = "CEDULA_VERDE"
    VTV = "VTV"


class DocumentoVehiculoCreate(BaseModel):
    tipo: TipoDocumentoVehiculo
    numero: str = Field(min_length=1, max_length=50)
    entidad_emisora: str | None = Field(default=None, max_length=255)
    fecha_emision: date
    fecha_vencimiento: date
    url_archivo: HttpUrl = Field(max_length=500)


class DocumentoVehiculo(DocumentoVehiculoCreate):
    url_archivo: AnyUrl = Field(max_length=500)
    id_vehiculo: int
    estado: EstadoDocumento


def documento_vehiculo_desde_dominio(
    id_vehiculo: int,
    documento: DocumentoVehiculoDominio,
    estado: EstadoDocumentoDominio,
) -> DocumentoVehiculo:
    return DocumentoVehiculo(
        tipo=TipoDocumentoVehiculo(documento.tipo.value),
        numero=documento.numero,
        entidad_emisora=documento.entidad_emisora,
        fecha_emision=documento.fecha_emision,
        fecha_vencimiento=documento.fecha_vencimiento,
        url_archivo=documento.url_archivo,
        id_vehiculo=id_vehiculo,
        estado=EstadoDocumento(estado.value),
    )
