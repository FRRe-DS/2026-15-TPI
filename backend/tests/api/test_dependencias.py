"""Pruebas del cableado de casos de uso con la unidad de trabajo (T074)."""

import sys
import types
from typing import Any

from app.api import dependencias
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

CASOS = [
    (dependencias.obtener_caso_crear_conductor, CrearConductor),
    (dependencias.obtener_caso_listar_conductores, ListarConductores),
    (dependencias.obtener_caso_obtener_conductor, ObtenerConductor),
    (
        dependencias.obtener_caso_consultar_habilitacion_conductor,
        ConsultarHabilitacionConductor,
    ),
    (
        dependencias.obtener_caso_accionar_habilitacion_conductor,
        AccionarHabilitacionConductor,
    ),
    (dependencias.obtener_caso_registrar_licencia, RegistrarLicencia),
    (dependencias.obtener_caso_registrar_vehiculo, RegistrarVehiculo),
    (dependencias.obtener_caso_listar_vehiculos, ListarVehiculos),
    (dependencias.obtener_caso_obtener_vehiculo, ObtenerVehiculo),
    (
        dependencias.obtener_caso_accionar_habilitacion_vehiculo,
        AccionarHabilitacionVehiculo,
    ),
]


class _UnidadDeTrabajoFalsa:
    """Sustituto de la unidad de trabajo de S1."""


class _SesionFalsa:
    def __init__(self) -> None:
        self.cerrada = False

    def close(self) -> None:
        self.cerrada = True


def _instalar_unidad_de_trabajo_sql(monkeypatch) -> type:
    """Registra un módulo falso con la unidad de trabajo de S1."""

    modulo = types.ModuleType(
        "app.infraestructura.repositorios.sql_unidad_de_trabajo"
    )

    class UnidadDeTrabajoSQL:
        def __init__(self, sesion: Any) -> None:
            self.sesion = sesion

    modulo.UnidadDeTrabajoSQL = UnidadDeTrabajoSQL
    monkeypatch.setitem(
        sys.modules,
        "app.infraestructura.repositorios.sql_unidad_de_trabajo",
        modulo,
    )
    return UnidadDeTrabajoSQL


def test_construye_cada_caso_de_uso_con_la_unidad_de_trabajo(monkeypatch) -> None:
    _instalar_unidad_de_trabajo_sql(monkeypatch)

    for proveedor, esperado in CASOS:
        caso = proveedor(_UnidadDeTrabajoFalsa())

        assert type(caso) is esperado


def test_entrega_la_unidad_de_trabajo_y_cierra_la_sesion(monkeypatch) -> None:
    unidad_de_trabajo_sql = _instalar_unidad_de_trabajo_sql(monkeypatch)
    sesion = _SesionFalsa()
    monkeypatch.setattr(dependencias, "_fabrica_de_sesiones", lambda: lambda: sesion)

    generador = dependencias.obtener_unidad_de_trabajo()
    unidad = next(generador)

    assert isinstance(unidad, unidad_de_trabajo_sql)
    assert unidad.sesion is sesion
    assert not sesion.cerrada

    generador.close()

    assert sesion.cerrada
