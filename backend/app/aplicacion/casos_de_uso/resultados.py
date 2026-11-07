from dataclasses import dataclass, field
from datetime import datetime

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
class DocumentoVehiculoConEstado:
    documento: DocumentoVehiculo
    estado: EstadoDocumento


@dataclass
class DocumentoDeVehiculo:
    id_vehiculo: int
    documento: DocumentoVehiculo
    estado: EstadoDocumento


@dataclass
class VehiculoDetalle:
    vehiculo: Vehiculo
    documentos: list[DocumentoVehiculoConEstado] = field(default_factory=list)


@dataclass
class HabilitacionVehiculoEventos:
    id_vehiculo: int
    estado: EstadoHabilitacion
    eventos: list[EventoHabilitacion]


@dataclass
class EstadoDelConductor:
    id_conductor: int
    estado: EstadoConductor
    id_vehiculo_activo: int | None
    actualizado: datetime | None

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
    id_conductor: int
    latitud: float | None
    longitud: float | None
    fecha_act_ubic: datetime | None
