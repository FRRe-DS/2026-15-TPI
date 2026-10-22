from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.api.esquemas.habilitacion import EstadoHabilitacion
from app.dominio.habilitacion import EstadoHabilitacion as EstadoHabilitacionDominio
from app.dominio.vehiculo import ServicioDelVehiculo
from app.dominio.vehiculo import TipoServicio as TipoServicioDominio
from app.dominio.vehiculo import TipoVehiculo as TipoVehiculoDominio
from app.dominio.vehiculo import Vehiculo as VehiculoDominio


class TipoVehiculo(StrEnum):
    AUTO = "AUTO"
    MOTO = "MOTO"


class TipoServicio(StrEnum):
    PASAJEROS = "PASAJEROS"
    ENVIOS = "ENVIOS"


class TipoServicioHabilitado(BaseModel):
    tipo: TipoServicio
    habilitado: bool


class VehiculoCreate(BaseModel):
    tipo: TipoVehiculo
    patente: str = Field(min_length=1, max_length=10)
    marca: str = Field(min_length=1, max_length=80)
    modelo: str = Field(min_length=1, max_length=80)
    anio: int = Field(ge=1900, le=2100)
    tipos_serv: list[TipoServicio] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )

    @field_validator("tipos_serv")
    @classmethod
    def _sin_repetidos(cls, tipos: list[TipoServicio]) -> list[TipoServicio]:
        if len(set(tipos)) != len(tipos):
            raise ValueError("Los tipos de servicio no pueden repetirse")
        return tipos


class VehiculoResumen(BaseModel):
    id: int
    tipo: TipoVehiculo
    patente: str
    marca: str
    modelo: str
    anio: int
    habilitacion: EstadoHabilitacion


class Vehiculo(BaseModel):
    id: int
    id_conductor: int
    tipo: TipoVehiculo
    patente: str
    marca: str
    modelo: str
    anio: int
    tipos_serv: list[TipoServicioHabilitado]
    documentos: list[dict] = Field(default_factory=list)
    habilitacion: EstadoHabilitacion


def _servicios(
    servicios: list[ServicioDelVehiculo],
) -> list[TipoServicioHabilitado]:
    return [
        TipoServicioHabilitado(
            tipo=TipoServicio(servicio.tipo.value),
            habilitado=servicio.habilitado,
        )
        for servicio in servicios
    ]


def vehiculo_resumen_desde_dominio(vehiculo: VehiculoDominio) -> VehiculoResumen:
    return VehiculoResumen(
        id=_id(vehiculo),
        tipo=TipoVehiculo(vehiculo.tipo.value),
        patente=vehiculo.patente,
        marca=vehiculo.marca,
        modelo=vehiculo.modelo,
        anio=vehiculo.anio,
        habilitacion=EstadoHabilitacion(
            EstadoHabilitacionDominio(vehiculo.habilitacion.value).value
        ),
    )


def vehiculo_desde_dominio(vehiculo: VehiculoDominio) -> Vehiculo:
    return Vehiculo(
        id=_id(vehiculo),
        id_conductor=_id_conductor(vehiculo),
        tipo=TipoVehiculo(vehiculo.tipo.value),
        patente=vehiculo.patente,
        marca=vehiculo.marca,
        modelo=vehiculo.modelo,
        anio=vehiculo.anio,
        tipos_serv=_servicios(vehiculo.tipos_servicio),
        documentos=[],
        habilitacion=EstadoHabilitacion(
            EstadoHabilitacionDominio(vehiculo.habilitacion.value).value
        ),
    )


def _id(vehiculo: VehiculoDominio) -> int:
    assert vehiculo.id is not None, "El vehículo debe estar persistido"
    return vehiculo.id


def _id_conductor(vehiculo: VehiculoDominio) -> int:
    assert vehiculo.id_conductor is not None, "El vehículo debe tener conductor"
    return vehiculo.id_conductor


def servicio_desde_esquema(tipo: TipoServicio) -> TipoServicioDominio:
    return TipoServicioDominio(tipo.value)


def tipo_vehiculo_desde_esquema(tipo: TipoVehiculo) -> TipoVehiculoDominio:
    return TipoVehiculoDominio(tipo.value)
