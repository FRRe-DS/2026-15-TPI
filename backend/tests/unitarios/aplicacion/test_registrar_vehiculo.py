"""Caso de uso `registrar_vehiculo` (POST /conductores/{id}/vehiculos).

Firmas bajo prueba:
    RegistrarVehiculo(uow: UnidadDeTrabajo, reloj: Reloj)
    RegistrarVehiculo.ejecutar(*, id_conductor, tipo: TipoVehiculo, patente, marca, modelo,
                               anio, tipos_servicio: list[TipoServicio]) -> VehiculoDetalle
    VehiculoDetalle(vehiculo: Vehiculo, documentos: list = [])
        el Vehiculo de dominio trae id, id_conductor, tipo, patente, marca, modelo, anio,
        tipos_servicio y habilitacion; `documentos` es siempre vacia en la Iteracion 1.

Alta: el vehiculo queda PENDIENTE, con todos sus tipos de servicio sin habilitar, y se
registra el evento ALTA en el historial del VEHICULO (no del conductor). El caso de uso
confirma con `uow.commit()` dentro del `with uow:`; ante un error no queda nada persistido.
Cuando fallan a la vez el conductor inexistente y los datos, la spec no fija cual error
gana; cada test deja en falta una sola cosa.
"""

from datetime import UTC, datetime

import pytest

from app.aplicacion.casos_de_uso.registrar_vehiculo import RegistrarVehiculo
from app.dominio.conductor import Conductor
from app.dominio.errores import DatosInvalidos, NoEncontrado, PatenteDuplicada
from app.dominio.habilitacion import AccionHabilitacion, EstadoHabilitacion
from app.dominio.vehiculo import TipoServicio, TipoVehiculo
from tests.unitarios.fakes.reloj_fijo import RelojFijo
from tests.unitarios.fakes.repositorios_en_memoria import UnidadDeTrabajoEnMemoria

AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)

DATOS_VALIDOS = {
    "tipo": TipoVehiculo.AUTO,
    "patente": "AB123CD",
    "marca": "Toyota",
    "modelo": "Etios",
    "anio": 2019,
    "tipos_servicio": [TipoServicio.PASAJEROS, TipoServicio.ENVIOS],
}


@pytest.fixture
def uow():
    return UnidadDeTrabajoEnMemoria()


@pytest.fixture
def registrar_vehiculo(uow):
    return RegistrarVehiculo(uow, RelojFijo(AHORA))


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


def test_crea_el_vehiculo_pendiente_con_sus_servicios_sin_habilitar(
    registrar_vehiculo, uow
):
    conductor = sembrar_conductor(uow)

    detalle = registrar_vehiculo.ejecutar(id_conductor=conductor.id, **DATOS_VALIDOS)

    vehiculo = detalle.vehiculo
    assert vehiculo.id is not None
    assert vehiculo.id_conductor == conductor.id
    assert vehiculo.tipo is TipoVehiculo.AUTO
    assert vehiculo.patente == "AB123CD"
    assert vehiculo.marca == "Toyota"
    assert vehiculo.modelo == "Etios"
    assert vehiculo.anio == 2019
    assert vehiculo.habilitacion is EstadoHabilitacion.PENDIENTE
    assert {s.tipo for s in vehiculo.tipos_servicio} == {
        TipoServicio.PASAJEROS,
        TipoServicio.ENVIOS,
    }
    assert [s.habilitado for s in vehiculo.tipos_servicio] == [False, False]
    assert detalle.documentos == []


def test_el_vehiculo_queda_confirmado_en_la_unidad_de_trabajo(registrar_vehiculo, uow):
    conductor = sembrar_conductor(uow)

    vehiculo = registrar_vehiculo.ejecutar(
        id_conductor=conductor.id, **DATOS_VALIDOS
    ).vehiculo

    guardado = uow.vehiculos.obtener(conductor.id, vehiculo.id)
    assert guardado is not None
    assert guardado.patente == "AB123CD"
    assert guardado.habilitacion is EstadoHabilitacion.PENDIENTE


def test_registra_el_evento_de_alta_en_el_historial_del_vehiculo(
    registrar_vehiculo, uow
):
    conductor = sembrar_conductor(uow)

    vehiculo = registrar_vehiculo.ejecutar(
        id_conductor=conductor.id, **DATOS_VALIDOS
    ).vehiculo

    historial = uow.habilitaciones.historial_vehiculo(vehiculo.id)
    assert len(historial) == 1
    alta = historial[0]
    assert alta.accion is AccionHabilitacion.ALTA
    assert alta.estado_anterior is None
    assert alta.estado_nuevo is EstadoHabilitacion.PENDIENTE
    assert alta.id_operador is None
    assert alta.motivo.strip() != ""
    assert alta.fecha == AHORA


def test_el_evento_de_alta_no_se_registra_en_el_historial_del_conductor(
    registrar_vehiculo, uow
):
    conductor = sembrar_conductor(uow)

    registrar_vehiculo.ejecutar(id_conductor=conductor.id, **DATOS_VALIDOS)

    assert uow.habilitaciones.historial_conductor(conductor.id) == []


@pytest.mark.parametrize(
    "mismo_conductor", [True, False], ids=["mismo_conductor", "otro_conductor"]
)
def test_rechaza_patente_duplicada_sin_dejar_vehiculo_ni_evento_extra(
    registrar_vehiculo, uow, mismo_conductor
):
    duenio = sembrar_conductor(uow, "30000001")
    otro = sembrar_conductor(uow, "30000002")
    primero = registrar_vehiculo.ejecutar(
        id_conductor=duenio.id, **DATOS_VALIDOS
    ).vehiculo
    id_que_repite = duenio.id if mismo_conductor else otro.id

    with pytest.raises(PatenteDuplicada):
        registrar_vehiculo.ejecutar(
            id_conductor=id_que_repite, **{**DATOS_VALIDOS, "marca": "Otra"}
        )

    assert [v.id for v in uow.vehiculos.listar_por_conductor(duenio.id)] == [primero.id]
    assert uow.vehiculos.listar_por_conductor(otro.id) == []
    assert len(uow.habilitaciones.historial_vehiculo(primero.id)) == 1
    assert uow.habilitaciones.historial_vehiculo(primero.id + 1) == []


def test_lanza_no_encontrado_si_el_conductor_no_existe_sin_guardar_nada(
    registrar_vehiculo, uow
):
    existente = sembrar_conductor(uow)
    id_inexistente = existente.id + 1

    with pytest.raises(NoEncontrado):
        registrar_vehiculo.ejecutar(id_conductor=id_inexistente, **DATOS_VALIDOS)

    assert uow.vehiculos.listar_por_conductor(id_inexistente) == []
    assert uow.vehiculos.listar_por_conductor(existente.id) == []
    assert uow.habilitaciones.historial_vehiculo(1) == []


@pytest.mark.parametrize(
    "dato_invalido",
    [
        {"tipos_servicio": []},
        {"tipos_servicio": [TipoServicio.ENVIOS, TipoServicio.ENVIOS]},
        {"tipo": "CAMION"},
        {"patente": ""},
        {"marca": "   "},
        {"modelo": ""},
        {"anio": "2019"},
        {"anio": 2019.5},
    ],
    ids=[
        "sin_tipos_de_servicio",
        "tipos_de_servicio_repetidos",
        "tipo_de_vehiculo_invalido",
        "patente_vacia",
        "marca_solo_espacios",
        "modelo_vacio",
        "anio_texto",
        "anio_decimal",
    ],
)
def test_datos_invalidos_lanzan_error_y_no_persisten_nada(
    registrar_vehiculo, uow, dato_invalido
):
    conductor = sembrar_conductor(uow)

    with pytest.raises(DatosInvalidos):
        registrar_vehiculo.ejecutar(
            id_conductor=conductor.id, **{**DATOS_VALIDOS, **dato_invalido}
        )

    assert uow.vehiculos.listar_por_conductor(conductor.id) == []
    assert uow.habilitaciones.historial_vehiculo(1) == []
