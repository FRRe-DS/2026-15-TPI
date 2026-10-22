from dataclasses import dataclass
from enum import Enum

from app.dominio.errores import DatosInvalidos
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.validaciones import exigir_texto


class TipoVehiculo(Enum):
    AUTO = "AUTO"
    MOTO = "MOTO"


class TipoServicio(Enum):
    PASAJEROS = "PASAJEROS"
    ENVIOS = "ENVIOS"


@dataclass
class ServicioDelVehiculo:
    tipo: TipoServicio
    habilitado: bool = False


@dataclass
class Vehiculo:
    tipo: TipoVehiculo
    patente: str
    marca: str
    modelo: str
    anio: int
    tipos_servicio: list[ServicioDelVehiculo]
    habilitacion: EstadoHabilitacion = EstadoHabilitacion.PENDIENTE
    id: int | None = None
    id_conductor: int | None = None

    @classmethod
    def crear(
        cls,
        *,
        tipo: TipoVehiculo,
        patente: str,
        marca: str,
        modelo: str,
        anio: int,
        tipos_servicio: list[TipoServicio],
    ) -> "Vehiculo":
        if not isinstance(tipo, TipoVehiculo):
            raise DatosInvalidos("El tipo de vehículo no es válido")
        exigir_texto("patente", patente)
        exigir_texto("marca", marca)
        exigir_texto("modelo", modelo)
        if not _es_entero(anio):
            raise DatosInvalidos("El año debe ser un número entero")
        _exigir_tipos_servicio_distintos(tipos_servicio)
        return cls(
            tipo=tipo,
            patente=patente,
            marca=marca,
            modelo=modelo,
            anio=anio,
            tipos_servicio=[ServicioDelVehiculo(servicio) for servicio in tipos_servicio],
        )


def _es_entero(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _exigir_tipos_servicio_distintos(tipos_servicio: list[TipoServicio]) -> None:
    if not tipos_servicio:
        raise DatosInvalidos("Se requiere al menos un tipo de servicio")
    if len(set(tipos_servicio)) != len(tipos_servicio):
        raise DatosInvalidos("Los tipos de servicio no pueden repetirse")
