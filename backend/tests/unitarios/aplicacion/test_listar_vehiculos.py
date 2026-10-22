"""Caso de uso `listar_vehiculos` (GET /conductores/{id}/vehiculos).

Firmas bajo prueba:
    ListarVehiculos(uow: UnidadDeTrabajo)
    ListarVehiculos.ejecutar(*, id_conductor, tipo=None, habilitacion=None) -> list[Vehiculo]

Devuelve solo los vehiculos del conductor pedido, en orden de alta; `tipo` y `habilitacion`
filtran y se combinan con AND. Sin coincidencias o sin vehiculos devuelve lista vacia.
Lanza NoEncontrado si el conductor no existe.
"""

import pytest
from app.aplicacion.casos_de_uso.listar_vehiculos import ListarVehiculos
from app.dominio.conductor import Conductor
from app.dominio.errores import NoEncontrado
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.vehiculo import TipoServicio, TipoVehiculo, Vehiculo

from tests.unitarios.fakes.repositorios_en_memoria import UnidadDeTrabajoEnMemoria

AUTO = TipoVehiculo.AUTO
MOTO = TipoVehiculo.MOTO
PENDIENTE = EstadoHabilitacion.PENDIENTE
APROBADA = EstadoHabilitacion.APROBADA


@pytest.fixture
def uow():
    return UnidadDeTrabajoEnMemoria()


@pytest.fixture
def listar_vehiculos(uow):
    return ListarVehiculos(uow)


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


def sembrar_vehiculo(uow, id_conductor, patente, tipo=AUTO, habilitacion=PENDIENTE):
    vehiculo = Vehiculo.crear(
        tipo=tipo,
        patente=patente,
        marca="Toyota",
        modelo="Etios",
        anio=2019,
        tipos_servicio=[TipoServicio.PASAJEROS],
    )
    vehiculo.id_conductor = id_conductor
    vehiculo.habilitacion = habilitacion
    guardado = uow.vehiculos.guardar(vehiculo)
    uow.commit()
    return guardado


def patentes(vehiculos):
    return [vehiculo.patente for vehiculo in vehiculos]


def test_sin_filtros_devuelve_los_vehiculos_del_conductor_en_orden_de_alta(listar_vehiculos, uow):
    conductor = sembrar_conductor(uow)
    for patente in ("AAA111", "BBB222", "CCC333"):
        sembrar_vehiculo(uow, conductor.id, patente)

    resultado = listar_vehiculos.ejecutar(id_conductor=conductor.id)

    assert patentes(resultado) == ["AAA111", "BBB222", "CCC333"]


def test_no_mezcla_los_vehiculos_de_otro_conductor(listar_vehiculos, uow):
    pedido = sembrar_conductor(uow, "30000001")
    otro = sembrar_conductor(uow, "30000002")
    sembrar_vehiculo(uow, pedido.id, "AAA111")
    sembrar_vehiculo(uow, otro.id, "BBB222")
    sembrar_vehiculo(uow, pedido.id, "CCC333")

    resultado = listar_vehiculos.ejecutar(id_conductor=pedido.id)

    assert patentes(resultado) == ["AAA111", "CCC333"]
    assert all(vehiculo.id_conductor == pedido.id for vehiculo in resultado)


@pytest.mark.parametrize(
    ("filtros", "patentes_esperadas"),
    [
        ({"tipo": AUTO}, ["AUTO-PEND", "AUTO-APROB"]),
        ({"tipo": MOTO}, ["MOTO-PEND", "MOTO-APROB"]),
        ({"habilitacion": APROBADA}, ["AUTO-APROB", "MOTO-APROB"]),
        ({"habilitacion": PENDIENTE}, ["AUTO-PEND", "MOTO-PEND"]),
        ({"tipo": MOTO, "habilitacion": APROBADA}, ["MOTO-APROB"]),
        ({"tipo": AUTO, "habilitacion": PENDIENTE}, ["AUTO-PEND"]),
    ],
    ids=[
        "por_tipo_auto",
        "por_tipo_moto",
        "por_habilitacion_aprobada",
        "por_habilitacion_pendiente",
        "moto_y_aprobada",
        "auto_y_pendiente",
    ],
)
def test_filtra_por_tipo_y_por_habilitacion_combinando_con_and(
    listar_vehiculos, uow, filtros, patentes_esperadas
):
    conductor = sembrar_conductor(uow)
    sembrar_vehiculo(uow, conductor.id, "AUTO-PEND", AUTO, PENDIENTE)
    sembrar_vehiculo(uow, conductor.id, "AUTO-APROB", AUTO, APROBADA)
    sembrar_vehiculo(uow, conductor.id, "MOTO-PEND", MOTO, PENDIENTE)
    sembrar_vehiculo(uow, conductor.id, "MOTO-APROB", MOTO, APROBADA)

    resultado = listar_vehiculos.ejecutar(id_conductor=conductor.id, **filtros)

    assert patentes(resultado) == patentes_esperadas


def test_los_filtros_se_aplican_solo_a_los_vehiculos_del_conductor_pedido(listar_vehiculos, uow):
    pedido = sembrar_conductor(uow, "30000001")
    otro = sembrar_conductor(uow, "30000002")
    sembrar_vehiculo(uow, pedido.id, "AAA111", AUTO)
    sembrar_vehiculo(uow, otro.id, "BBB222", MOTO)

    assert listar_vehiculos.ejecutar(id_conductor=pedido.id, tipo=MOTO) == []


def test_filtros_sin_coincidencias_devuelven_lista_vacia_sin_error(listar_vehiculos, uow):
    conductor = sembrar_conductor(uow)
    sembrar_vehiculo(uow, conductor.id, "AAA111", AUTO, PENDIENTE)

    assert listar_vehiculos.ejecutar(id_conductor=conductor.id, habilitacion=APROBADA) == []


def test_un_conductor_sin_vehiculos_devuelve_lista_vacia_sin_error(listar_vehiculos, uow):
    conductor = sembrar_conductor(uow)

    assert listar_vehiculos.ejecutar(id_conductor=conductor.id) == []


def test_lanza_no_encontrado_si_el_conductor_no_existe(listar_vehiculos, uow):
    existente = sembrar_conductor(uow)

    with pytest.raises(NoEncontrado):
        listar_vehiculos.ejecutar(id_conductor=existente.id + 1)
