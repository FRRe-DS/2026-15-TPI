from enum import Enum


class EstadoHabilitacion(Enum):
    PENDIENTE = "PENDIENTE"
    OBSERVADA = "OBSERVADA"
    APROBADA = "APROBADA"
    SUSPENDIDA = "SUSPENDIDA"
    RECHAZADA = "RECHAZADA"
