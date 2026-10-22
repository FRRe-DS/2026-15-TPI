from dataclasses import dataclass

from app.dominio.conductor import Conductor
from app.dominio.documento import Documento, EstadoDocumento
from app.dominio.vehiculo import Vehiculo


@dataclass
class DocumentoConEstado:
    documento: Documento
    estado: EstadoDocumento


@dataclass
class ConductorDetalle:
    conductor: Conductor
    documentos: list[DocumentoConEstado]
    vehiculos: list[Vehiculo]
