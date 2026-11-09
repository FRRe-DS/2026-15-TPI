import re
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from app.dominio.errores import DatosInvalidos
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.validaciones import exigir_texto

PATRON_DNI = re.compile(r"[0-9]{7,8}")
PATRON_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
CENTESIMAS = Decimal("0.01")


class EstadoConductor(Enum):
    DESCONECTADO = "DESCONECTADO"
    CONECTADO = "CONECTADO"
    DISPONIBLE = "DISPONIBLE"
    OCUPADO = "OCUPADO"


@dataclass
class Conductor:
    dni: str
    nombre: str
    apellido: str
    telefono: str
    email: str
    habilitacion: EstadoHabilitacion = EstadoHabilitacion.PENDIENTE
    estado: EstadoConductor = EstadoConductor.DESCONECTADO
    id_vehiculo_activo: int | None = None
    fecha_ultimo_cambio_estado: datetime | None = None
    suma_puntajes: int = 0
    cantidad_calificaciones: int = 0
    id: int | None = None
    latitud: float | None = None
    longitud: float | None = None
    fecha_act_ubic: datetime | None = None
    fecha_alta: datetime | None = None

    @classmethod
    def crear(
        cls, *, dni: str, nombre: str, apellido: str, telefono: str, email: str
    ) -> "Conductor":
        if not PATRON_DNI.fullmatch(dni):
            raise DatosInvalidos("El DNI debe tener 7 u 8 dígitos")
        exigir_texto("nombre", nombre)
        exigir_texto("apellido", apellido)
        exigir_texto("telefono", telefono)
        if not PATRON_EMAIL.fullmatch(email):
            raise DatosInvalidos("El email no tiene un formato válido")
        return cls(dni=dni, nombre=nombre, apellido=apellido, telefono=telefono, email=email)

    @property
    def puntaje_promedio(self) -> Decimal | None:
        if self.suma_puntajes < 0 or self.cantidad_calificaciones < 0:
            raise DatosInvalidos("Los totales de puntajes no pueden ser negativos")
        if self.cantidad_calificaciones == 0:
            if self.suma_puntajes != 0:
                raise DatosInvalidos("La suma de puntajes debe ser 0 cuando no hay calificaciones")
            return None
        promedio = Decimal(self.suma_puntajes) / Decimal(self.cantidad_calificaciones)
        return promedio.quantize(CENTESIMAS, rounding=ROUND_HALF_UP)

    @property
    def tiene_ubicacion(self) -> bool:
        return self.latitud is not None and self.longitud is not None

    def fijar_ubicacion(self, latitud: float, longitud: float, ahora: datetime) -> None:
        if not -90 <= latitud <= 90:
            raise DatosInvalidos("La latitud debe estar entre -90 y 90")
        if not -180 <= longitud <= 180:
            raise DatosInvalidos("La longitud debe estar entre -180 y 180")
        self.latitud = latitud
        self.longitud = longitud
        self.fecha_act_ubic = ahora
