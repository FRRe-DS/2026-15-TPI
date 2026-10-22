"""Proveedores de dependencias de la API.

Cada caso de uso se construye con una unidad de trabajo respaldada por una
fábrica de sesiones de SQLAlchemy y el reloj del sistema. La unidad abre y
cierra una sesión en cada transacción. Los tests reemplazan estos proveedores mediante
``app.dependency_overrides``.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker

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
from app.aplicacion.puertos.reloj import Reloj
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.infraestructura.db.sesion import crear_sessionmaker


class RelojDelSistema(Reloj):
    def ahora(self) -> datetime:
        return datetime.now(UTC)

    def hoy(self) -> date:
        return self.ahora().date()


@lru_cache(maxsize=1)
def _fabrica_de_sesiones() -> sessionmaker[Session]:
    """Crea una única fábrica de sesiones por proceso."""
    return crear_sessionmaker()


def obtener_unidad_de_trabajo() -> Iterator[UnidadDeTrabajo]:
    """Entrega una unidad que administra su sesión por transacción."""
    from app.infraestructura.repositorios.sql_unidad_de_trabajo import SqlUnidadDeTrabajo

    yield SqlUnidadDeTrabajo(_fabrica_de_sesiones())


UnidadDeTrabajoInyectada = Annotated[
    UnidadDeTrabajo,
    Depends(obtener_unidad_de_trabajo),
]


def obtener_caso_crear_conductor(
    uow: UnidadDeTrabajoInyectada,
) -> CrearConductor:
    return CrearConductor(uow, RelojDelSistema())


def obtener_caso_listar_conductores(
    uow: UnidadDeTrabajoInyectada,
) -> ListarConductores:
    return ListarConductores(uow, RelojDelSistema())


def obtener_caso_obtener_conductor(
    uow: UnidadDeTrabajoInyectada,
) -> ObtenerConductor:
    return ObtenerConductor(uow, RelojDelSistema())


def obtener_caso_consultar_habilitacion_conductor(
    uow: UnidadDeTrabajoInyectada,
) -> ConsultarHabilitacionConductor:
    return ConsultarHabilitacionConductor(uow)


def obtener_caso_accionar_habilitacion_conductor(
    uow: UnidadDeTrabajoInyectada,
) -> AccionarHabilitacionConductor:
    return AccionarHabilitacionConductor(uow, RelojDelSistema())


def obtener_caso_registrar_licencia(
    uow: UnidadDeTrabajoInyectada,
) -> RegistrarLicencia:
    return RegistrarLicencia(uow, RelojDelSistema())


def obtener_caso_registrar_vehiculo(
    uow: UnidadDeTrabajoInyectada,
) -> RegistrarVehiculo:
    return RegistrarVehiculo(uow, RelojDelSistema())


def obtener_caso_listar_vehiculos(
    uow: UnidadDeTrabajoInyectada,
) -> ListarVehiculos:
    return ListarVehiculos(uow)


def obtener_caso_obtener_vehiculo(
    uow: UnidadDeTrabajoInyectada,
) -> ObtenerVehiculo:
    return ObtenerVehiculo(uow)


def obtener_caso_accionar_habilitacion_vehiculo(
    uow: UnidadDeTrabajoInyectada,
) -> AccionarHabilitacionVehiculo:
    return AccionarHabilitacionVehiculo(uow, RelojDelSistema())
