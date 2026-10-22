from dataclasses import dataclass, field

from app.dominio.conductor import Conductor
from app.dominio.documento import Documento, EstadoDocumento
from app.dominio.habilitacion import EstadoHabilitacion, EventoHabilitacion
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


@dataclass
class HabilitacionResumen:
    id_conductor: int
    estado: EstadoHabilitacion
    historial: list[EventoHabilitacion]


@dataclass
class HabilitacionEventos:
    id_conductor: int
    estado: EstadoHabilitacion
    eventos: list[EventoHabilitacion]


@dataclass
class DocumentoDeConductor:
    id_conductor: int
    documento: Documento
    estado: EstadoDocumento


@dataclass
class VehiculoDetalle:
    vehiculo: Vehiculo
    documentos: list = field(default_factory=list)
