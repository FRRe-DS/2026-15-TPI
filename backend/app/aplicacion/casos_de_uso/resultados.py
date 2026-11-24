from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.dominio.conductor import Conductor, EstadoConductor
from app.dominio.documento import Documento, EstadoDocumento
from app.dominio.documento_vehiculo import DocumentoVehiculo
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
    id_conductor: UUID
    estado: EstadoHabilitacion
    historial: list[EventoHabilitacion]


@dataclass
class HabilitacionEventos:
    id_conductor: UUID
    estado: EstadoHabilitacion
    eventos: list[EventoHabilitacion]


@dataclass
class DocumentoDeConductor:
    id_conductor: UUID
    documento: Documento
    estado: EstadoDocumento


@dataclass
class DocumentoVehiculoConEstado:
    documento: DocumentoVehiculo
    estado: EstadoDocumento


@dataclass
class DocumentoDeVehiculo:
    id_vehiculo: UUID
    documento: DocumentoVehiculo
    estado: EstadoDocumento


@dataclass
class VehiculoDetalle:
    vehiculo: Vehiculo
    documentos: list[DocumentoVehiculoConEstado] = field(default_factory=list)


@dataclass
class HabilitacionVehiculoEventos:
    id_vehiculo: UUID
    estado: EstadoHabilitacion
    eventos: list[EventoHabilitacion]


@dataclass
class EstadoDelConductor:
    id_conductor: UUID
    estado: EstadoConductor
    id_vehiculo_activo: UUID | None
    actualizado: datetime

    @classmethod
    def desde_conductor(cls, conductor: Conductor) -> "EstadoDelConductor":
        # Un conductor que nunca cambió de estado se informa con su fecha de alta.
        actualizado = conductor.fecha_ultimo_cambio_estado or conductor.fecha_alta
        return cls(
            id_conductor=conductor.id,
            estado=conductor.estado,
            id_vehiculo_activo=conductor.id_vehiculo_activo,
            actualizado=actualizado,
        )


@dataclass
class UbicacionDelConductor:
    id_conductor: UUID
    latitud: float | None
    longitud: float | None
    fecha_act_ubic: datetime | None
