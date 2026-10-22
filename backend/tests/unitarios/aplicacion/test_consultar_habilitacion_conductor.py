"""Caso de uso `consultar_habilitacion_conductor` (GET /conductores/{id}/habilitacion).

Firmas bajo prueba:
    ConsultarHabilitacionConductor(uow: UnidadDeTrabajo)
    ConsultarHabilitacionConductor.ejecutar(*, id_conductor) -> HabilitacionResumen
    HabilitacionResumen(id_conductor, estado: EstadoHabilitacion,
                        historial: list[EventoHabilitacion])

El estado es el actual del conductor; el historial va en orden cronologico ascendente por
`fecha` (no por orden de registro). Lanza NoEncontrado si el conductor no existe.
"""

from datetime import UTC, datetime

import pytest
from app.aplicacion.casos_de_uso.consultar_habilitacion_conductor import (
    ConsultarHabilitacionConductor,
)
from app.aplicacion.casos_de_uso.crear_conductor import CrearConductor
from app.dominio.conductor import Conductor
from app.dominio.errores import NoEncontrado
from app.dominio.habilitacion import (
    AccionHabilitacion,
    EstadoHabilitacion,
    EventoHabilitacion,
)

from tests.unitarios.fakes.reloj_fijo import RelojFijo
from tests.unitarios.fakes.repositorios_en_memoria import UnidadDeTrabajoEnMemoria

AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)


@pytest.fixture
def uow():
    return UnidadDeTrabajoEnMemoria()


@pytest.fixture
def consultar_habilitacion(uow):
    return ConsultarHabilitacionConductor(uow)


def guardar_conductor(uow, dni, **estado):
    conductor = Conductor.crear(
        dni=dni,
        nombre="Ana",
        apellido="Perez",
        telefono="+54 379 4000000",
        email="ana@example.com",
    )
    for atributo, valor in estado.items():
        setattr(conductor, atributo, valor)
    guardado = uow.conductores.guardar(conductor)
    uow.commit()
    return guardado


def registrar_evento(uow, id_conductor, accion, anterior, nuevo, hora, motivo):
    evento = EventoHabilitacion(
        accion=accion,
        estado_anterior=anterior,
        estado_nuevo=nuevo,
        motivo=motivo,
        id_operador=7,
        fecha=datetime(2026, 6, 1, hora, 0, tzinfo=UTC),
    )
    uow.habilitaciones.registrar_evento_conductor(id_conductor, evento)
    uow.commit()
    return evento


def test_un_conductor_recien_creado_muestra_pendiente_con_el_alta_como_primer_evento(
    consultar_habilitacion, uow
):
    id_conductor = (
        CrearConductor(uow, RelojFijo(AHORA))
        .ejecutar(
            dni="30123456",
            nombre="Ana",
            apellido="Perez",
            telefono="+54 379 4000000",
            email="ana@example.com",
        )
        .conductor.id
    )

    resumen = consultar_habilitacion.ejecutar(id_conductor=id_conductor)

    assert resumen.id_conductor == id_conductor
    assert resumen.estado is EstadoHabilitacion.PENDIENTE
    assert [evento.accion for evento in resumen.historial] == [AccionHabilitacion.ALTA]
    assert resumen.historial[0].estado_nuevo is EstadoHabilitacion.PENDIENTE
    assert resumen.historial[0].fecha == AHORA


def test_devuelve_el_estado_actual_del_conductor_y_su_historial(consultar_habilitacion, uow):
    conductor = guardar_conductor(uow, "30000001", habilitacion=EstadoHabilitacion.APROBADA)
    alta = registrar_evento(
        uow,
        conductor.id,
        AccionHabilitacion.ALTA,
        None,
        EstadoHabilitacion.PENDIENTE,
        hora=9,
        motivo="Alta",
    )
    aprobacion = registrar_evento(
        uow,
        conductor.id,
        AccionHabilitacion.APROBAR,
        EstadoHabilitacion.PENDIENTE,
        EstadoHabilitacion.APROBADA,
        hora=10,
        motivo="Documentacion completa",
    )

    resumen = consultar_habilitacion.ejecutar(id_conductor=conductor.id)

    assert resumen.id_conductor == conductor.id
    assert resumen.estado is EstadoHabilitacion.APROBADA
    assert resumen.historial == [alta, aprobacion]


def test_el_historial_va_en_orden_cronologico_por_fecha_y_no_por_registro(
    consultar_habilitacion, uow
):
    conductor = guardar_conductor(uow, "30000001", habilitacion=EstadoHabilitacion.APROBADA)
    suspension = registrar_evento(
        uow,
        conductor.id,
        AccionHabilitacion.SUSPENDER,
        EstadoHabilitacion.APROBADA,
        EstadoHabilitacion.SUSPENDIDA,
        hora=12,
        motivo="Suspension",
    )
    alta = registrar_evento(
        uow,
        conductor.id,
        AccionHabilitacion.ALTA,
        None,
        EstadoHabilitacion.PENDIENTE,
        hora=9,
        motivo="Alta",
    )
    aprobacion = registrar_evento(
        uow,
        conductor.id,
        AccionHabilitacion.APROBAR,
        EstadoHabilitacion.PENDIENTE,
        EstadoHabilitacion.APROBADA,
        hora=10,
        motivo="Aprobacion",
    )

    resumen = consultar_habilitacion.ejecutar(id_conductor=conductor.id)

    assert resumen.historial == [alta, aprobacion, suspension]


def test_el_historial_de_otro_conductor_no_se_mezcla(consultar_habilitacion, uow):
    pedido = guardar_conductor(uow, "30000001")
    otro = guardar_conductor(uow, "30000002")
    propio = registrar_evento(
        uow,
        pedido.id,
        AccionHabilitacion.ALTA,
        None,
        EstadoHabilitacion.PENDIENTE,
        hora=9,
        motivo="Alta propia",
    )
    registrar_evento(
        uow,
        otro.id,
        AccionHabilitacion.ALTA,
        None,
        EstadoHabilitacion.PENDIENTE,
        hora=8,
        motivo="Alta ajena",
    )

    resumen = consultar_habilitacion.ejecutar(id_conductor=pedido.id)

    assert resumen.historial == [propio]


def test_un_conductor_sin_eventos_devuelve_historial_vacio(consultar_habilitacion, uow):
    conductor = guardar_conductor(uow, "30000001")

    resumen = consultar_habilitacion.ejecutar(id_conductor=conductor.id)

    assert resumen.historial == []


def test_lanza_no_encontrado_si_el_conductor_no_existe(consultar_habilitacion, uow):
    existente = guardar_conductor(uow, "30000001")

    with pytest.raises(NoEncontrado):
        consultar_habilitacion.ejecutar(id_conductor=existente.id + 1)


def test_los_eventos_del_historial_traen_id_distinto_y_el_posterior_es_mayor(
    consultar_habilitacion, uow
):
    conductor = guardar_conductor(uow, "30000001", habilitacion=EstadoHabilitacion.APROBADA)
    registrar_evento(
        uow,
        conductor.id,
        AccionHabilitacion.ALTA,
        None,
        EstadoHabilitacion.PENDIENTE,
        hora=9,
        motivo="Alta",
    )
    registrar_evento(
        uow,
        conductor.id,
        AccionHabilitacion.APROBAR,
        EstadoHabilitacion.PENDIENTE,
        EstadoHabilitacion.APROBADA,
        hora=10,
        motivo="Aprobacion",
    )

    resumen = consultar_habilitacion.ejecutar(id_conductor=conductor.id)

    ids = [evento.id for evento in resumen.historial]
    assert len(ids) == 2
    assert all(id_evento is not None for id_evento in ids)
    assert ids == sorted(set(ids))  # el alta (anterior) tiene menor id que la aprobacion
