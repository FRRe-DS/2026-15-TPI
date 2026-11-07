"""Caso de uso `listar_tipos_servicio_vehiculo`
(GET /conductores/{id}/vehiculos/{id_vehiculo}/tipos-servicio).

Firmas bajo prueba:
    ListarTiposServicioVehiculo(uow: UnidadDeTrabajo)
    ListarTiposServicioVehiculo.ejecutar(*, id_conductor, id_vehiculo)
        -> list[ServicioDelVehiculo]

Devuelve cada tipo de servicio del vehiculo con su `habilitado`, sin garantizar un orden: el
repositorio SQL los ordena por nombre y el fake en memoria por registro, asi que los tests los
comparan como conjunto. Lanza NoEncontrado si el vehiculo no existe o es de otro conductor.
"""

import pytest
from app.aplicacion.casos_de_uso.listar_tipos_servicio_vehiculo import (
    ListarTiposServicioVehiculo,
)
from app.dominio.conductor import Conductor
from app.dominio.errores import NoEncontrado
from app.dominio.vehiculo import TipoServicio, TipoVehiculo, Vehiculo

from tests.unitarios.fakes.repositorios_en_memoria import UnidadDeTrabajoEnMemoria


@pytest.fixture
def uow():
    return UnidadDeTrabajoEnMemoria()


@pytest.fixture
def listar_tipos_servicio(uow):
    return ListarTiposServicioVehiculo(uow)


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


def sembrar_vehiculo(uow, id_conductor, patente="AB123CD", habilitados=()):
    vehiculo = Vehiculo.crear(
        tipo=TipoVehiculo.AUTO,
        patente=patente,
        marca="Toyota",
        modelo="Etios",
        anio=2019,
        tipos_servicio=[TipoServicio.PASAJEROS, TipoServicio.ENVIOS],
    )
    vehiculo.id_conductor = id_conductor
    for servicio in vehiculo.tipos_servicio:
        servicio.habilitado = servicio.tipo in habilitados
    guardado = uow.vehiculos.guardar(vehiculo)
    uow.commit()
    return guardado


def test_devuelve_cada_tipo_de_servicio_con_su_habilitado(listar_tipos_servicio, uow):
    conductor = sembrar_conductor(uow)
    vehiculo = sembrar_vehiculo(uow, conductor.id, habilitados={TipoServicio.ENVIOS})

    resultado = listar_tipos_servicio.ejecutar(id_conductor=conductor.id, id_vehiculo=vehiculo.id)

    assert {(servicio.tipo, servicio.habilitado) for servicio in resultado} == {
        (TipoServicio.PASAJEROS, False),
        (TipoServicio.ENVIOS, True),
    }


def test_un_vehiculo_sin_tipos_habilitados_los_devuelve_todos_en_falso(listar_tipos_servicio, uow):
    conductor = sembrar_conductor(uow)
    vehiculo = sembrar_vehiculo(uow, conductor.id)

    resultado = listar_tipos_servicio.ejecutar(id_conductor=conductor.id, id_vehiculo=vehiculo.id)

    assert [servicio.habilitado for servicio in resultado] == [False, False]


def test_no_mezcla_los_tipos_de_servicio_de_otro_vehiculo(listar_tipos_servicio, uow):
    conductor = sembrar_conductor(uow)
    pedido = sembrar_vehiculo(uow, conductor.id, "AAA111")
    sembrar_vehiculo(uow, conductor.id, "BBB222", habilitados={TipoServicio.PASAJEROS})

    resultado = listar_tipos_servicio.ejecutar(id_conductor=conductor.id, id_vehiculo=pedido.id)

    assert [servicio.habilitado for servicio in resultado] == [False, False]


def test_lanza_no_encontrado_si_el_vehiculo_no_existe(listar_tipos_servicio, uow):
    conductor = sembrar_conductor(uow)
    vehiculo = sembrar_vehiculo(uow, conductor.id)

    with pytest.raises(NoEncontrado):
        listar_tipos_servicio.ejecutar(id_conductor=conductor.id, id_vehiculo=vehiculo.id + 1)


def test_lanza_no_encontrado_si_el_vehiculo_es_de_otro_conductor(listar_tipos_servicio, uow):
    duenio = sembrar_conductor(uow, "30000001")
    otro = sembrar_conductor(uow, "30000002")
    vehiculo_del_duenio = sembrar_vehiculo(uow, duenio.id)

    with pytest.raises(NoEncontrado):
        listar_tipos_servicio.ejecutar(id_conductor=otro.id, id_vehiculo=vehiculo_del_duenio.id)
