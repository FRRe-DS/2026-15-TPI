import re
from dataclasses import dataclass

from app.dominio.errores import DatosInvalidos
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.validaciones import exigir_texto

PATRON_DNI = re.compile(r"[0-9]{7,8}")
PATRON_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


@dataclass
class Conductor:
    dni: str
    nombre: str
    apellido: str
    telefono: str
    email: str
    habilitacion: EstadoHabilitacion = EstadoHabilitacion.PENDIENTE
    conectado: bool = False
    disponible: bool = False
    id: int | None = None

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
