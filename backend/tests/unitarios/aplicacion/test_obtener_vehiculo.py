"""Caso de uso `obtener_vehiculo` (GET /conductores/{id}/vehiculos/{id_vehiculo}).

Firmas bajo prueba:
    ObtenerVehiculo(uow: UnidadDeTrabajo)
    ObtenerVehiculo.ejecutar(*, id_conductor, id_vehiculo) -> VehiculoDetalle

Devuelve el vehiculo con todos sus datos y `documentos` vacio. Lanza NoEncontrado si el
conductor no existe, si el vehiculo no existe o si el vehiculo es de otro conductor.
"""

import pytest
from app.aplicacion.casos_de_uso.obtener_vehiculo import ObtenerVehiculo
from app.dominio.conductor import Conductor
from app.dominio.errores import NoEncontrado
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.vehiculo import TipoServicio, TipoVehiculo, Vehiculo

from tests.unitarios.fakes.repositorios_en_memoria import UnidadDeTrabajoEnMemoria


@pytest.fixture
def uow():
    return UnidadDeTrabajoEnMemoria()


@pytest.fixture
def obtener_vehiculo(uow):
    return ObtenerVehiculo(uow)


def sembrar_conductor(uow, dni="30123456"):
    conductor = Conductor.crear(
        dni=dni,
        nombre="Ana",
        apellido="Perez",
        telefono="+54 379 4000000",
        email="ana@example.com",
    )
    guardado = uow.conductores.guardar(conductor)
    uow.commit()
    return guardado


def sembrar_vehiculo(uow, id_conductor, patente="AB123CD"):
    vehiculo = Vehiculo.crear(
        tipo=TipoVehiculo.MOTO,
        patente=patente,
        marca="Honda",
        modelo="Wave",
        anio=2021,
        tipos_servicio=[TipoServicio.PASAJEROS, TipoServicio.ENVIOS],
    )
    vehiculo.id_conductor = id_conductor
    vehiculo.habilitacion = EstadoHabilitacion.APROBADA
    vehiculo.tipos_servicio[1].habilitado = True  # ENVIOS habilitado, PASAJEROS no
    guardado = uow.vehiculos.guardar(vehiculo)
    uow.commit()
    return guardado


def test_devuelve_el_vehiculo_con_todos_sus_datos(obtener_vehiculo, uow):
    conductor = sembrar_conductor(uow)
    sembrado = sembrar_vehiculo(uow, conductor.id)

    detalle = obtener_vehiculo.ejecutar(id_conductor=conductor.id, id_vehiculo=sembrado.id)

    vehiculo = detalle.vehiculo
    assert vehiculo.id == sembrado.id
    assert vehiculo.id_conductor == conductor.id
    assert vehiculo.tipo is TipoVehiculo.MOTO
    assert vehiculo.patente == "AB123CD"
    assert vehiculo.marca == "Honda"
    assert vehiculo.modelo == "Wave"
    assert vehiculo.anio == 2021
    assert vehiculo.habilitacion is EstadoHabilitacion.APROBADA
    assert {s.tipo: s.habilitado for s in vehiculo.tipos_servicio} == {
        TipoServicio.PASAJEROS: False,
        TipoServicio.ENVIOS: True,
    }


def test_los_documentos_del_vehiculo_vienen_vacios(obtener_vehiculo, uow):
    conductor = sembrar_conductor(uow)
    sembrado = sembrar_vehiculo(uow, conductor.id)

    detalle = obtener_vehiculo.ejecutar(id_conductor=conductor.id, id_vehiculo=sembrado.id)

    assert detalle.documentos == []


def test_lanza_no_encontrado_si_el_conductor_no_existe(obtener_vehiculo, uow):
    conductor = sembrar_conductor(uow)
    sembrado = sembrar_vehiculo(uow, conductor.id)

    with pytest.raises(NoEncontrado):
        obtener_vehiculo.ejecutar(id_conductor=conductor.id + 1, id_vehiculo=sembrado.id)


def test_lanza_no_encontrado_si_el_vehiculo_no_existe(obtener_vehiculo, uow):
    conductor = sembrar_conductor(uow)
    sembrado = sembrar_vehiculo(uow, conductor.id)

    with pytest.raises(NoEncontrado):
        obtener_vehiculo.ejecutar(id_conductor=conductor.id, id_vehiculo=sembrado.id + 1)


def test_lanza_no_encontrado_si_el_vehiculo_pertenece_a_otro_conductor(obtener_vehiculo, uow):
    duenio = sembrar_conductor(uow, "30000001")
    otro = sembrar_conductor(uow, "30000002")
    vehiculo_del_duenio = sembrar_vehiculo(uow, duenio.id)

    with pytest.raises(NoEncontrado):
        obtener_vehiculo.ejecutar(id_conductor=otro.id, id_vehiculo=vehiculo_del_duenio.id)
