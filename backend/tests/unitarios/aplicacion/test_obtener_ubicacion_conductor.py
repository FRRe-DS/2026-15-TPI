"""Caso de uso `obtener_ubicacion_conductor` (GET /conductores/{id}/ubicacion).

Firmas bajo prueba:
    ObtenerUbicacionConductor(uow: UnidadDeTrabajo)
    ObtenerUbicacionConductor.ejecutar(*, id_conductor) -> UbicacionDelConductor
    UbicacionDelConductor(id_conductor, latitud: float | None, longitud: float | None,
                          fecha_act_ubic: datetime | None)

Un conductor sin ubicacion devuelve los tres datos en None (nunca 0.0). Lanza NoEncontrado si el
conductor no existe.
"""

from datetime import UTC, datetime

import pytest
from app.aplicacion.casos_de_uso.obtener_ubicacion_conductor import ObtenerUbicacionConductor
from app.dominio.conductor import Conductor
from app.dominio.errores import NoEncontrado

from tests.unitarios.fakes.repositorios_en_memoria import UnidadDeTrabajoEnMemoria

LATITUD = -27.4511
LONGITUD = -58.9867
FECHA_UBICACION = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)


@pytest.fixture
def uow():
    return UnidadDeTrabajoEnMemoria()


@pytest.fixture
def obtener_ubicacion(uow):
    return ObtenerUbicacionConductor(uow)


def guardar_conductor(uow, **atributos):
    conductor = Conductor.crear(
        dni="30123456",
        nombre="Ana",
        apellido="Perez",
        telefono="+54 379 4000000",
        email="ana@example.com",
    )
    for atributo, valor in atributos.items():
        setattr(conductor, atributo, valor)
    guardado = uow.conductores.guardar(conductor)
    uow.commit()
    return guardado


def test_devuelve_latitud_longitud_y_fecha_de_la_ubicacion(uow, obtener_ubicacion):
    conductor = guardar_conductor(
        uow, latitud=LATITUD, longitud=LONGITUD, fecha_act_ubic=FECHA_UBICACION
    )

    resultado = obtener_ubicacion.ejecutar(id_conductor=conductor.id)

    assert resultado.id_conductor == conductor.id
    assert resultado.latitud == LATITUD
    assert resultado.longitud == LONGITUD
    assert resultado.fecha_act_ubic == FECHA_UBICACION


def test_sin_ubicacion_devuelve_los_tres_datos_en_none_y_nunca_cero(uow, obtener_ubicacion):
    conductor = guardar_conductor(uow)

    resultado = obtener_ubicacion.ejecutar(id_conductor=conductor.id)

    assert resultado.latitud is None
    assert resultado.longitud is None
    assert resultado.fecha_act_ubic is None


def test_conductor_inexistente_lanza_no_encontrado(uow, obtener_ubicacion):
    conductor = guardar_conductor(uow)

    with pytest.raises(NoEncontrado):
        obtener_ubicacion.ejecutar(id_conductor=conductor.id + 1)
