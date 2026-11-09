"""Esquemas de estado y ubicación del conductor (operaciones 13, 14 y 15)."""

from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.api.esquemas.conductor import EstadoOperativo
from app.aplicacion.casos_de_uso.resultados import EstadoDelConductor, UbicacionDelConductor

__all__ = [
    "EstadoConductor",
    "EstadoConductorRequest",
    "EstadoOperativo",
    "EstadoPedido",
    "UbicacionConductor",
    "estado_desde_dominio",
    "ubicacion_desde_dominio",
]

_CAMPOS_SIN_NULO = ("estado", "latitud", "longitud")


class EstadoPedido(StrEnum):
    """Estados que el conductor puede pedir: `OCUPADO` lo asigna M3 al aceptar una solicitud."""

    DESCONECTADO = "DESCONECTADO"
    CONECTADO = "CONECTADO"
    DISPONIBLE = "DISPONIBLE"


class EstadoConductorRequest(BaseModel):
    estado: EstadoPedido | None = None
    # Se distingue "no informado" de `null` con `model_fields_set`: `null` quita el vehículo.
    id_vehiculo_activo: int | None = None
    latitud: float | None = Field(default=None, ge=-90, le=90)
    longitud: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def _validar_pedido(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("El pedido debe informar al menos un campo")
        for campo in _CAMPOS_SIN_NULO:
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} no admite null")
        if (self.latitud is None) != (self.longitud is None):
            raise ValueError("latitud y longitud se informan juntas")
        return self


class EstadoConductor(BaseModel):
    id_conductor: int
    estado: EstadoOperativo
    id_vehiculo_activo: int | None = None
    actualizado: datetime


class UbicacionConductor(BaseModel):
    id_conductor: int
    latitud: float | None
    longitud: float | None
    fecha_act_ubic: datetime | None


def estado_desde_dominio(estado: EstadoDelConductor) -> EstadoConductor:
    return EstadoConductor(
        id_conductor=estado.id_conductor,
        estado=EstadoOperativo(estado.estado.value),
        id_vehiculo_activo=estado.id_vehiculo_activo,
        actualizado=estado.actualizado,
    )


def ubicacion_desde_dominio(ubicacion: UbicacionDelConductor) -> UbicacionConductor:
    return UbicacionConductor(
        id_conductor=ubicacion.id_conductor,
        latitud=ubicacion.latitud,
        longitud=ubicacion.longitud,
        fecha_act_ubic=ubicacion.fecha_act_ubic,
    )
