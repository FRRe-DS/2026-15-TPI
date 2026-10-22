"""Pruebas del cableado de casos de uso con la unidad de trabajo (T074)."""

from unittest.mock import Mock

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
from app.infraestructura.repositorios.sql_unidad_de_trabajo import SqlUnidadDeTrabajo
from sqlalchemy.orm import Session

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


def test_construye_cada_caso_de_uso_con_la_unidad_de_trabajo() -> None:

    for proveedor, esperado in CASOS:
        caso = proveedor(_UnidadDeTrabajoFalsa())

        assert type(caso) is esperado


def test_entrega_la_unidad_de_trabajo_y_cierra_la_sesion(monkeypatch) -> None:
    sesion = Mock(spec=Session)
    fabrica = Mock(return_value=sesion)
    monkeypatch.setattr(dependencias, "_fabrica_de_sesiones", lambda: fabrica)

    generador = dependencias.obtener_unidad_de_trabajo()
    unidad = next(generador)
    assert isinstance(unidad, SqlUnidadDeTrabajo)
    fabrica.assert_not_called()

    with unidad:
        fabrica.assert_called_once_with()
        sesion.close.assert_not_called()

    sesion.rollback.assert_called_once_with()
    sesion.close.assert_called_once_with()
    generador.close()
