"""Caso de uso `accionar_habilitacion_conductor` (POST /conductores/{id}/habilitacion).

Firmas bajo prueba:
    AccionarHabilitacionConductor(uow: UnidadDeTrabajo, reloj: Reloj)
    AccionarHabilitacionConductor.ejecutar(*, id_conductor, accion: AccionHabilitacion,
                                           motivo, id_operador) -> HabilitacionEventos
    HabilitacionEventos(id_conductor, estado: EstadoHabilitacion,
                        eventos: list[EventoHabilitacion])
        `eventos` es el historial completo del conductor en orden cronologico, con el
        evento recien registrado al final.

Reglas: la transicion debe estar en la matriz; APROBAR exige al menos una licencia VIGENTE
segun `reloj.hoy()` (vence hoy cuenta como vigente); OBSERVAR, RECHAZAR y SUSPENDER no
exigen licencia; el motivo es obligatorio; el conductor se toma con
`uow.bloquear_conductor`. El estado y el evento se confirman juntos con `uow.commit()`;
ante cualquier error no queda nada persistido.

Cuando fallan a la vez la matriz, la licencia o el motivo, la spec no fija cual error
gana; cada test deja en falta una sola regla.
"""

from datetime import UTC, date, datetime, timedelta

import pytest
from app.aplicacion.casos_de_uso.accionar_habilitacion_conductor import (
    AccionarHabilitacionConductor,
)
from app.dominio.conductor import Conductor
from app.dominio.documento import Documento, TipoDocumento
from app.dominio.errores import (
    DatosInvalidos,
    LicenciaVigenteRequerida,
    NoEncontrado,
    TransicionInvalida,
)
from app.dominio.habilitacion import (
    AccionHabilitacion,
    EstadoHabilitacion,
    EventoHabilitacion,
)

from tests.unitarios.fakes.reloj_fijo import RelojFijo
from tests.unitarios.fakes.repositorios_en_memoria import UnidadDeTrabajoEnMemoria

AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
HOY = AHORA.date()
ID_OPERADOR = 7
MOTIVO = "Documentacion revisada"

PENDIENTE = EstadoHabilitacion.PENDIENTE
OBSERVADA = EstadoHabilitacion.OBSERVADA
APROBADA = EstadoHabilitacion.APROBADA
SUSPENDIDA = EstadoHabilitacion.SUSPENDIDA
RECHAZADA = EstadoHabilitacion.RECHAZADA

APROBAR = AccionHabilitacion.APROBAR
OBSERVAR = AccionHabilitacion.OBSERVAR
SUSPENDER = AccionHabilitacion.SUSPENDER
RECHAZAR = AccionHabilitacion.RECHAZAR
ALTA = AccionHabilitacion.ALTA

AYER = HOY - timedelta(days=1)
MANANA = HOY + timedelta(days=1)


class UnidadDeTrabajoQueRegistraBloqueos(UnidadDeTrabajoEnMemoria):
    def __init__(self):
        super().__init__()
        self.conductores_bloqueados = []

    def bloquear_conductor(self, id_conductor):
        self.conductores_bloqueados.append(id_conductor)
        return super().bloquear_conductor(id_conductor)


@pytest.fixture
def uow():
    return UnidadDeTrabajoQueRegistraBloqueos()


@pytest.fixture
def reloj():
    return RelojFijo(AHORA)


@pytest.fixture
def accionar(uow, reloj):
    return AccionarHabilitacionConductor(uow, reloj)


def sembrar_conductor(uow, estado=PENDIENTE, vencimientos_de_licencias=()):
    conductor = Conductor.crear(
        dni="30123456",
        nombre="Ana",
        apellido="Perez",
        telefono="+54 379 4000000",
        email="ana@example.com",
    )
    conductor.habilitacion = estado
    conductor = uow.conductores.guardar(conductor)
    for numero, vencimiento in enumerate(vencimientos_de_licencias, start=1):
        licencia = Documento.crear(
            tipo=TipoDocumento.LICENCIA,
            numero=f"LIC-{numero}",
            categoria=None,
            fecha_emision=date(2020, 1, 1),
            fecha_vencimiento=vencimiento,
            url_archivo="https://almacen.example.com/licencias/lic.pdf",
        )
        uow.documentos.guardar(conductor.id, licencia)
    uow.commit()
    return conductor


def sembrar_evento_de_alta(uow, id_conductor):
    alta = EventoHabilitacion(
        accion=ALTA,
        estado_anterior=None,
        estado_nuevo=PENDIENTE,
        motivo="Alta del conductor",
        id_operador=None,
        fecha=AHORA - timedelta(days=30),
    )
    uow.habilitaciones.registrar_evento_conductor(id_conductor, alta)
    uow.commit()
    return alta


def estado_guardado(uow, id_conductor):
    return uow.conductores.obtener(id_conductor).habilitacion


@pytest.mark.parametrize(
    "vencimientos_de_licencias",
    [[HOY], [MANANA], [AYER, MANANA]],
    ids=["vence_hoy", "vence_manana", "una_vencida_y_una_vigente"],
)
def test_aprobar_con_licencia_vigente_pasa_a_aprobada_y_registra_el_evento(
    accionar, uow, vencimientos_de_licencias
):
    conductor = sembrar_conductor(uow, PENDIENTE, vencimientos_de_licencias)
    alta = sembrar_evento_de_alta(uow, conductor.id)

    resultado = accionar.ejecutar(
        id_conductor=conductor.id,
        accion=APROBAR,
        motivo=MOTIVO,
        id_operador=ID_OPERADOR,
    )

    historial = uow.habilitaciones.historial_conductor(conductor.id)
    assert len(historial) == 2
    assert historial[0] == alta
    evento = historial[1]
    assert evento.accion is APROBAR
    assert evento.estado_anterior is PENDIENTE
    assert evento.estado_nuevo is APROBADA
    assert evento.motivo == MOTIVO
    assert evento.id_operador == ID_OPERADOR
    assert evento.fecha == AHORA
    assert estado_guardado(uow, conductor.id) is APROBADA
    assert resultado.id_conductor == conductor.id
    assert resultado.estado is APROBADA
    assert resultado.eventos == [alta, evento]


@pytest.mark.parametrize(
    "vencimientos_de_licencias",
    [[], [AYER], [AYER, date(2026, 1, 1)]],
    ids=["sin_licencias", "solo_una_vencida", "solo_vencidas"],
)
def test_aprobar_sin_licencia_vigente_lanza_error_y_no_cambia_nada(
    accionar, uow, vencimientos_de_licencias
):
    conductor = sembrar_conductor(uow, PENDIENTE, vencimientos_de_licencias)
    alta = sembrar_evento_de_alta(uow, conductor.id)

    with pytest.raises(LicenciaVigenteRequerida):
        accionar.ejecutar(
            id_conductor=conductor.id,
            accion=APROBAR,
            motivo=MOTIVO,
            id_operador=ID_OPERADOR,
        )

    assert estado_guardado(uow, conductor.id) is PENDIENTE
    assert uow.habilitaciones.historial_conductor(conductor.id) == [alta]


@pytest.mark.parametrize(
    ("estado_inicial", "accion"),
    [
        (APROBADA, OBSERVAR),
        (APROBADA, APROBAR),
        (PENDIENTE, SUSPENDER),
        (PENDIENTE, ALTA),
        (RECHAZADA, APROBAR),
        (RECHAZADA, OBSERVAR),
        (RECHAZADA, SUSPENDER),
        (RECHAZADA, RECHAZAR),
    ],
    ids=lambda valor: valor.name,
)
def test_transicion_no_permitida_lanza_error_y_no_persiste_nada(
    accionar, uow, estado_inicial, accion
):
    conductor = sembrar_conductor(uow, estado_inicial, [MANANA])
    alta = sembrar_evento_de_alta(uow, conductor.id)

    with pytest.raises(TransicionInvalida):
        accionar.ejecutar(
            id_conductor=conductor.id,
            accion=accion,
            motivo=MOTIVO,
            id_operador=ID_OPERADOR,
        )

    assert estado_guardado(uow, conductor.id) is estado_inicial
    assert uow.habilitaciones.historial_conductor(conductor.id) == [alta]


@pytest.mark.parametrize(
    ("estado_inicial", "accion", "estado_esperado"),
    [
        (PENDIENTE, OBSERVAR, OBSERVADA),
        (PENDIENTE, RECHAZAR, RECHAZADA),
        (OBSERVADA, RECHAZAR, RECHAZADA),
        (APROBADA, SUSPENDER, SUSPENDIDA),
        (SUSPENDIDA, RECHAZAR, RECHAZADA),
    ],
    ids=lambda valor: valor.name,
)
def test_observar_rechazar_y_suspender_no_exigen_licencia(
    accionar, uow, estado_inicial, accion, estado_esperado
):
    conductor = sembrar_conductor(uow, estado_inicial, [])

    resultado = accionar.ejecutar(
        id_conductor=conductor.id,
        accion=accion,
        motivo=MOTIVO,
        id_operador=ID_OPERADOR,
    )

    assert resultado.estado is estado_esperado
    assert estado_guardado(uow, conductor.id) is estado_esperado
    [evento] = uow.habilitaciones.historial_conductor(conductor.id)
    assert evento.accion is accion
    assert evento.estado_anterior is estado_inicial
    assert evento.estado_nuevo is estado_esperado


def test_suspender_y_luego_aprobar_quedan_ambos_en_el_historial_en_orden(accionar, uow, reloj):
    conductor = sembrar_conductor(uow, APROBADA, [date(2029, 1, 1)])

    accionar.ejecutar(
        id_conductor=conductor.id,
        accion=SUSPENDER,
        motivo="Documentacion en revision",
        id_operador=ID_OPERADOR,
    )
    reloj.avanzar(dias=1)
    resultado = accionar.ejecutar(
        id_conductor=conductor.id,
        accion=APROBAR,
        motivo="Documentacion regularizada",
        id_operador=ID_OPERADOR,
    )

    historial = uow.habilitaciones.historial_conductor(conductor.id)
    assert [(e.accion, e.estado_anterior, e.estado_nuevo) for e in historial] == [
        (SUSPENDER, APROBADA, SUSPENDIDA),
        (APROBAR, SUSPENDIDA, APROBADA),
    ]
    assert estado_guardado(uow, conductor.id) is APROBADA
    assert resultado.eventos == historial


def test_reaprobar_tambien_exige_licencia_vigente_al_dia_de_hoy(accionar, uow, reloj):
    conductor = sembrar_conductor(uow, APROBADA, [HOY])
    accionar.ejecutar(
        id_conductor=conductor.id,
        accion=SUSPENDER,
        motivo="Suspension",
        id_operador=ID_OPERADOR,
    )
    reloj.avanzar(dias=1)  # la licencia que vencia hoy ya esta vencida

    with pytest.raises(LicenciaVigenteRequerida):
        accionar.ejecutar(
            id_conductor=conductor.id,
            accion=APROBAR,
            motivo="Reaprobacion",
            id_operador=ID_OPERADOR,
        )

    assert estado_guardado(uow, conductor.id) is SUSPENDIDA
    assert len(uow.habilitaciones.historial_conductor(conductor.id)) == 1


@pytest.mark.parametrize("motivo", ["", "   "])
def test_motivo_vacio_lanza_datos_invalidos_y_no_persiste_nada(accionar, uow, motivo):
    conductor = sembrar_conductor(uow, PENDIENTE, [MANANA])
    alta = sembrar_evento_de_alta(uow, conductor.id)

    with pytest.raises(DatosInvalidos):
        accionar.ejecutar(
            id_conductor=conductor.id,
            accion=APROBAR,
            motivo=motivo,
            id_operador=ID_OPERADOR,
        )

    assert estado_guardado(uow, conductor.id) is PENDIENTE
    assert uow.habilitaciones.historial_conductor(conductor.id) == [alta]


def test_lanza_no_encontrado_si_el_conductor_no_existe(accionar, uow):
    existente = sembrar_conductor(uow)

    with pytest.raises(NoEncontrado):
        accionar.ejecutar(
            id_conductor=existente.id + 1,
            accion=OBSERVAR,
            motivo=MOTIVO,
            id_operador=ID_OPERADOR,
        )

    assert uow.habilitaciones.historial_conductor(existente.id + 1) == []


def test_toma_el_conductor_con_bloqueo_de_fila(accionar, uow):
    conductor = sembrar_conductor(uow, PENDIENTE, [])

    accionar.ejecutar(
        id_conductor=conductor.id,
        accion=OBSERVAR,
        motivo=MOTIVO,
        id_operador=ID_OPERADOR,
    )

    assert uow.conductores_bloqueados == [conductor.id]


def test_los_eventos_devueltos_traen_id_distinto_y_el_nuevo_es_mayor_que_el_del_alta(accionar, uow):
    conductor = sembrar_conductor(uow, PENDIENTE, [MANANA])
    sembrar_evento_de_alta(uow, conductor.id)

    accionar.ejecutar(
        id_conductor=conductor.id, accion=APROBAR, motivo=MOTIVO, id_operador=ID_OPERADOR
    )
    resultado = accionar.ejecutar(
        id_conductor=conductor.id, accion=SUSPENDER, motivo=MOTIVO, id_operador=ID_OPERADOR
    )

    ids = [evento.id for evento in resultado.eventos]
    assert len(ids) == 3
    assert all(id_evento is not None for id_evento in ids)
    assert ids == sorted(set(ids))  # distintos y crecientes: el alta primero, el nuevo ultimo
