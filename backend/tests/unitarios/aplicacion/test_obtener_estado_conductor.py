"""Caso de uso `obtener_estado_conductor` (GET /conductores/{id}/estado).

Firmas bajo prueba:
    ObtenerEstadoConductor(uow: UnidadDeTrabajo)
    ObtenerEstadoConductor.ejecutar(*, id_conductor) -> EstadoDelConductor
    EstadoDelConductor(id_conductor, estado: EstadoConductor, id_vehiculo_activo: int | None,
                       actualizado: datetime | None)

`actualizado` es `fecha_ultimo_cambio_estado`; si el estado nunca cambio, la fecha de alta del
conductor. El resultado no incluye la ubicacion. Lanza NoEncontrado si el conductor no existe.
"""

from datetime import UTC, datetime

import pytest
from app.aplicacion.casos_de_uso.obtener_estado_conductor import ObtenerEstadoConductor
from app.dominio.conductor import Conductor, EstadoConductor
from app.dominio.errores import NoEncontrado

from tests.unitarios.fakes.repositorios_en_memoria import UnidadDeTrabajoEnMemoria

FECHA_DE_ALTA = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
FECHA_DE_CAMBIO = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
ID_VEHICULO_ACTIVO = 5


@pytest.fixture
def uow():
    return UnidadDeTrabajoEnMemoria()


@pytest.fixture
def obtener_estado(uow):
    return ObtenerEstadoConductor(uow)


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


def test_devuelve_estado_vehiculo_activo_y_fecha_del_ultimo_cambio(uow, obtener_estado):
    conductor = guardar_conductor(
        uow,
        estado=EstadoConductor.DISPONIBLE,
        id_vehiculo_activo=ID_VEHICULO_ACTIVO,
        fecha_alta=FECHA_DE_ALTA,
        fecha_ultimo_cambio_estado=FECHA_DE_CAMBIO,
    )

    resultado = obtener_estado.ejecutar(id_conductor=conductor.id)

    assert resultado.id_conductor == conductor.id
    assert resultado.estado is EstadoConductor.DISPONIBLE
    assert resultado.id_vehiculo_activo == ID_VEHICULO_ACTIVO
    assert resultado.actualizado == FECHA_DE_CAMBIO


def test_sin_vehiculo_activo_devuelve_id_nulo(uow, obtener_estado):
    conductor = guardar_conductor(uow, fecha_alta=FECHA_DE_ALTA)

    resultado = obtener_estado.ejecutar(id_conductor=conductor.id)

    assert resultado.id_vehiculo_activo is None


def test_si_el_estado_nunca_cambio_actualizado_es_la_fecha_de_alta(uow, obtener_estado):
    conductor = guardar_conductor(uow, fecha_alta=FECHA_DE_ALTA)
    assert conductor.fecha_ultimo_cambio_estado is None

    resultado = obtener_estado.ejecutar(id_conductor=conductor.id)

    assert resultado.estado is EstadoConductor.DESCONECTADO
    assert resultado.actualizado == FECHA_DE_ALTA


def test_el_resultado_no_incluye_la_ubicacion(uow, obtener_estado):
    conductor = guardar_conductor(
        uow, latitud=-27.4511, longitud=-58.9867, fecha_alta=FECHA_DE_ALTA
    )

    resultado = obtener_estado.ejecutar(id_conductor=conductor.id)

    assert not hasattr(resultado, "latitud")
    assert not hasattr(resultado, "longitud")
    assert not hasattr(resultado, "fecha_act_ubic")


def test_conductor_inexistente_lanza_no_encontrado(uow, obtener_estado):
    conductor = guardar_conductor(uow)

    with pytest.raises(NoEncontrado):
        obtener_estado.ejecutar(id_conductor=conductor.id + 1)
