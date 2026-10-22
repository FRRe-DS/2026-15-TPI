"""Caso de uso `crear_conductor` (POST /conductores).

Firmas bajo prueba:
    CrearConductor(uow: UnidadDeTrabajo, reloj: Reloj)
    CrearConductor.ejecutar(*, dni, nombre, apellido, telefono, email) -> ConductorDetalle
    ConductorDetalle(conductor: Conductor, documentos: list[DocumentoConEstado],
                     vehiculos: list[Vehiculo])

Alta: el conductor queda PENDIENTE (conectado y disponible en falso), con documentos y
vehiculos vacios, y se registra el evento ALTA en su historial (estado_anterior e
id_operador nulos, fecha = reloj.ahora()). El caso de uso confirma con `uow.commit()`
dentro del `with uow:`; ante un error no queda nada persistido.
"""

from datetime import UTC, datetime

import pytest

from app.aplicacion.casos_de_uso.crear_conductor import CrearConductor
from app.dominio.errores import DatosInvalidos, DniDuplicado
from app.dominio.habilitacion import AccionHabilitacion, EstadoHabilitacion
from tests.unitarios.fakes.reloj_fijo import RelojFijo
from tests.unitarios.fakes.repositorios_en_memoria import UnidadDeTrabajoEnMemoria

AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)

DATOS_VALIDOS = {
    "dni": "30123456",
    "nombre": "Ana",
    "apellido": "Perez",
    "telefono": "+54 379 4000000",
    "email": "ana@example.com",
}


@pytest.fixture
def uow():
    return UnidadDeTrabajoEnMemoria()


@pytest.fixture
def crear_conductor(uow):
    return CrearConductor(uow, RelojFijo(AHORA))


def test_crea_el_conductor_pendiente_y_sin_conexion(crear_conductor):
    detalle = crear_conductor.ejecutar(**DATOS_VALIDOS)

    conductor = detalle.conductor
    assert conductor.id is not None
    assert conductor.dni == DATOS_VALIDOS["dni"]
    assert conductor.nombre == DATOS_VALIDOS["nombre"]
    assert conductor.apellido == DATOS_VALIDOS["apellido"]
    assert conductor.telefono == DATOS_VALIDOS["telefono"]
    assert conductor.email == DATOS_VALIDOS["email"]
    assert conductor.habilitacion is EstadoHabilitacion.PENDIENTE
    assert conductor.conectado is False
    assert conductor.disponible is False


def test_el_detalle_del_conductor_nuevo_no_tiene_documentos_ni_vehiculos(
    crear_conductor,
):
    detalle = crear_conductor.ejecutar(**DATOS_VALIDOS)

    assert detalle.documentos == []
    assert detalle.vehiculos == []


def test_registra_el_evento_de_alta_en_el_historial_del_conductor(crear_conductor, uow):
    id_conductor = crear_conductor.ejecutar(**DATOS_VALIDOS).conductor.id

    historial = uow.habilitaciones.historial_conductor(id_conductor)

    assert len(historial) == 1
    alta = historial[0]
    assert alta.accion is AccionHabilitacion.ALTA
    assert alta.estado_anterior is None
    assert alta.estado_nuevo is EstadoHabilitacion.PENDIENTE
    assert alta.id_operador is None
    assert alta.motivo.strip() != ""
    assert alta.fecha == AHORA


def test_el_conductor_queda_confirmado_en_la_unidad_de_trabajo(crear_conductor, uow):
    id_conductor = crear_conductor.ejecutar(**DATOS_VALIDOS).conductor.id

    guardado = uow.conductores.obtener(id_conductor)

    assert guardado is not None
    assert guardado.dni == DATOS_VALIDOS["dni"]
    assert len(uow.habilitaciones.historial_conductor(id_conductor)) == 1


def test_rechaza_dni_duplicado_sin_dejar_conductor_ni_evento_extra(
    crear_conductor, uow
):
    primero = crear_conductor.ejecutar(**DATOS_VALIDOS).conductor

    with pytest.raises(DniDuplicado):
        crear_conductor.ejecutar(**{**DATOS_VALIDOS, "email": "otra@example.com"})

    assert [c.id for c in uow.conductores.listar()] == [primero.id]
    assert len(uow.habilitaciones.historial_conductor(primero.id)) == 1
    assert uow.habilitaciones.historial_conductor(primero.id + 1) == []


@pytest.mark.parametrize(
    "dato_invalido",
    [
        {"dni": "1234567a"},
        {"dni": "123456"},
        {"email": "sin-arroba"},
        {"nombre": "   "},
    ],
    ids=["dni_con_letra", "dni_corto", "email_sin_formato", "nombre_vacio"],
)
def test_rechaza_datos_invalidos_sin_persistir_nada(
    crear_conductor, uow, dato_invalido
):
    with pytest.raises(DatosInvalidos):
        crear_conductor.ejecutar(**{**DATOS_VALIDOS, **dato_invalido})

    assert uow.conductores.listar() == []
    assert uow.habilitaciones.historial_conductor(1) == []
