"""Infraestructura de persistencia del módulo M3.

Expone el metadata declarativo, los modelos y los helpers de sesión. La URL de
conexión nunca se hardcodea: se resuelve desde ``DATABASE_URL``.
"""

from __future__ import annotations

from app.infraestructura.db.modelos import (
    Base,
    Conductor,
    DocumentoConductor,
    HabilitacionEventoConductor,
    HabilitacionEventoVehiculo,
    Vehiculo,
    VehiculoTipoServicio,
)
from app.infraestructura.db.sesion import (
    crear_engine,
    crear_sessionmaker,
    obtener_database_url,
    sesion,
)

__all__ = [
    "Base",
    "Conductor",
    "DocumentoConductor",
    "HabilitacionEventoConductor",
    "HabilitacionEventoVehiculo",
    "Vehiculo",
    "VehiculoTipoServicio",
    "crear_engine",
    "crear_sessionmaker",
    "obtener_database_url",
    "sesion",
]
