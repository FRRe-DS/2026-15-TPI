import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.api.esquemas.documento import DocumentoConductor, documento_desde_dominio
from app.api.esquemas.habilitacion import EstadoHabilitacion
from app.api.esquemas.vehiculo import (
    VehiculoResumen,
    vehiculo_resumen_desde_dominio,
)
from app.aplicacion.casos_de_uso.resultados import ConductorDetalle

PATRON_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


class EstadoOperativo(StrEnum):
    DESCONECTADO = "DESCONECTADO"
    CONECTADO = "CONECTADO"
    DISPONIBLE = "DISPONIBLE"
    OCUPADO = "OCUPADO"


class ConductorCreate(BaseModel):
    dni: str = Field(pattern=r"^[0-9]{7,8}$", max_length=8)
    nombre: str = Field(min_length=1, max_length=100)
    apellido: str = Field(min_length=1, max_length=100)
    telefono: str = Field(min_length=1, max_length=30)
    email: str = Field(
        max_length=255,
        json_schema_extra={"format": "email"},
    )

    @field_validator("email")
    @classmethod
    def _email_valido(cls, email: str) -> str:
        if not PATRON_EMAIL.fullmatch(email):
            raise ValueError("El email no tiene un formato válido")
        return email


class Conductor(ConductorCreate):
    id: int
    documentos: list[DocumentoConductor]
    vehiculos: list[VehiculoResumen]
    habilitacion: EstadoHabilitacion
    estado: EstadoOperativo
    puntaje_promedio: float | None = Field(default=None, ge=1, le=5)
    cantidad_calificaciones: int = Field(default=0, ge=0)


class ConductorConUbicacion(Conductor):
    id_vehiculo_activo: int | None = None
    latitud: float | None = None
    longitud: float | None = None
    fecha_act_ubic: datetime | None = None


def conductor_desde_detalle(
    detalle: ConductorDetalle,
) -> ConductorConUbicacion:
    conductor = detalle.conductor
    assert conductor.id is not None, "El conductor debe estar persistido"
    return ConductorConUbicacion(
        id=conductor.id,
        dni=conductor.dni,
        nombre=conductor.nombre,
        apellido=conductor.apellido,
        telefono=conductor.telefono,
        email=conductor.email,
        documentos=[
            documento_desde_dominio(conductor.id, documento.documento, documento.estado)
            for documento in detalle.documentos
        ],
        vehiculos=[vehiculo_resumen_desde_dominio(vehiculo) for vehiculo in detalle.vehiculos],
        habilitacion=EstadoHabilitacion(conductor.habilitacion.value),
        estado=EstadoOperativo(conductor.estado.value),
        puntaje_promedio=(
            float(promedio) if (promedio := conductor.puntaje_promedio) is not None else None
        ),
        cantidad_calificaciones=conductor.cantidad_calificaciones,
        id_vehiculo_activo=conductor.id_vehiculo_activo,
        latitud=conductor.latitud,
        longitud=conductor.longitud,
        fecha_act_ubic=conductor.fecha_act_ubic,
    )


def conductor_creado(detalle: ConductorDetalle) -> Conductor:
    datos = conductor_desde_detalle(detalle).model_dump(
        exclude={"id_vehiculo_activo", "latitud", "longitud", "fecha_act_ubic"}
    )
    return Conductor(**datos)
