"""Proveedores de dependencias de la API.

En esta PR quedan declarados los puntos de inyección de los casos de uso.
El cableado con los repositorios SQL y la sesión se completa en T074
(``feat/s2-endpoints-vehiculo``), cuando S1 y S3 estén integrados.
Mientras tanto, los tests de la API reemplazan estos proveedores por
simulados mediante ``app.dependency_overrides``.
"""

from __future__ import annotations

from app.aplicacion.casos_de_uso.accionar_habilitacion_conductor import (
    AccionarHabilitacionConductor,
)
from app.aplicacion.casos_de_uso.accionar_habilitacion_vehiculo import (
    AccionarHabilitacionVehiculo,
)
from app.aplicacion.casos_de_uso.consultar_habilitacion_conductor import (
    ConsultarHabilitacionConductor,
)
from app.aplicacion.casos_de_uso.crear_conductor import CrearConductor
from app.aplicacion.casos_de_uso.listar_conductores import ListarConductores
from app.aplicacion.casos_de_uso.listar_vehiculos import ListarVehiculos
from app.aplicacion.casos_de_uso.obtener_conductor import ObtenerConductor
from app.aplicacion.casos_de_uso.obtener_vehiculo import ObtenerVehiculo
from app.aplicacion.casos_de_uso.registrar_licencia import RegistrarLicencia
from app.aplicacion.casos_de_uso.registrar_vehiculo import RegistrarVehiculo


def _pendiente(nombre: str) -> RuntimeError:
    return RuntimeError(
        f"El caso de uso {nombre} todavía no está cableado. "
        "Se completa en T074 cuando estén disponibles los repositorios SQL de S1."
    )


def obtener_caso_crear_conductor() -> CrearConductor:
    raise _pendiente("crear_conductor")


def obtener_caso_listar_conductores() -> ListarConductores:
    raise _pendiente("listar_conductores")


def obtener_caso_obtener_conductor() -> ObtenerConductor:
    raise _pendiente("obtener_conductor")


def obtener_caso_consultar_habilitacion_conductor() -> ConsultarHabilitacionConductor:
    raise _pendiente("consultar_habilitacion_conductor")


def obtener_caso_accionar_habilitacion_conductor() -> AccionarHabilitacionConductor:
    raise _pendiente("accionar_habilitacion_conductor")


def obtener_caso_registrar_licencia() -> RegistrarLicencia:
    raise _pendiente("registrar_licencia")


def obtener_caso_registrar_vehiculo() -> RegistrarVehiculo:
    raise _pendiente("registrar_vehiculo")


def obtener_caso_listar_vehiculos() -> ListarVehiculos:
    raise _pendiente("listar_vehiculos")


def obtener_caso_obtener_vehiculo() -> ObtenerVehiculo:
    raise _pendiente("obtener_vehiculo")


def obtener_caso_accionar_habilitacion_vehiculo() -> AccionarHabilitacionVehiculo:
    raise _pendiente("accionar_habilitacion_vehiculo")
