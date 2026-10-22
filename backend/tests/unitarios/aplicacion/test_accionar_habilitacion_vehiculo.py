"""Caso de uso `accionar_habilitacion_vehiculo`
(POST /conductores/{id}/vehiculos/{id_vehiculo}/habilitacion).

Firmas bajo prueba:
    AccionarHabilitacionVehiculo(uow: UnidadDeTrabajo, reloj: Reloj)
    AccionarHabilitacionVehiculo.ejecutar(*, id_conductor, id_vehiculo,
                                          accion: AccionHabilitacion, motivo,
                                          id_operador) -> HabilitacionVehiculoEventos
    HabilitacionVehiculoEventos(id_vehiculo, estado: EstadoHabilitacion,
                                eventos: list[EventoHabilitacion])
        `eventos` es el historial completo del vehiculo en orden cronologico, con el
        evento recien registrado al final.

Reglas: la transicion debe estar en la matriz (la misma del conductor, pero sin regla de
licencia: APROBAR no exige documentos); el motivo es obligatorio; el vehiculo se toma con
`uow.bloquear_vehiculo(id_conductor, id_vehiculo)`; un vehiculo inexistente, de un
conductor inexistente o de otro conductor es NoEncontrado. El estado y el evento se
confirman juntos con `uow.commit()`; ante cualquier error no queda nada persistido. La
habilitacion de los tipos de servicio no cambia (llega en la Iteracion 2).
"""

import itertools
from datetime import UTC, datetime, timedelta

import pytest

from app.aplicacion.casos_de_uso.accionar_habilitacion_vehiculo import (
    AccionarHabilitacionVehiculo,
)
from app.dominio.conductor import Conductor
from app.dominio.errores import DatosInvalidos, NoEncontrado, TransicionInvalida
from app.dominio.habilitacion import (
    AccionHabilitacion,
    EstadoHabilitacion,
    EventoHabilitacion,
)
from app.dominio.vehiculo import TipoServicio, TipoVehiculo, Vehiculo
from tests.unitarios.fakes.reloj_fijo import RelojFijo
from tests.unitarios.fakes.repositorios_en_memoria import UnidadDeTrabajoEnMemoria

AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
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

TRANSICIONES_VALIDAS = {
    (PENDIENTE, APROBAR): APROBADA,
    (PENDIENTE, OBSERVAR): OBSERVADA,
    (PENDIENTE, RECHAZAR): RECHAZADA,
    (OBSERVADA, APROBAR): APROBADA,
    (OBSERVADA, RECHAZAR): RECHAZADA,
    (APROBADA, SUSPENDER): SUSPENDIDA,
    (SUSPENDIDA, APROBAR): APROBADA,
    (SUSPENDIDA, RECHAZAR): RECHAZADA,
}

TRANSICIONES_NO_PERMITIDAS = [
    combinacion
    for combinacion in itertools.product(EstadoHabilitacion, AccionHabilitacion)
    if combinacion not in TRANSICIONES_VALIDAS
]


class UnidadDeTrabajoQueRegistraBloqueos(UnidadDeTrabajoEnMemoria):
    def __init__(self):
        super().__init__()
        self.vehiculos_bloqueados = []

    def bloquear_vehiculo(self, id_conductor, id_vehiculo):
        self.vehiculos_bloqueados.append((id_conductor, id_vehiculo))
        return super().bloquear_vehiculo(id_conductor, id_vehiculo)


@pytest.fixture
def uow():
    return UnidadDeTrabajoQueRegistraBloqueos()


@pytest.fixture
def reloj():
    return RelojFijo(AHORA)


@pytest.fixture
def accionar(uow, reloj):
    return AccionarHabilitacionVehiculo(uow, reloj)


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


def sembrar_vehiculo(uow, id_conductor, estado=PENDIENTE, patente="AB123CD"):
    vehiculo = Vehiculo.crear(
        tipo=TipoVehiculo.AUTO,
        patente=patente,
        marca="Toyota",
        modelo="Etios",
        anio=2019,
        tipos_servicio=[TipoServicio.PASAJEROS, TipoServicio.ENVIOS],
    )
    vehiculo.id_conductor = id_conductor
    vehiculo.habilitacion = estado
    guardado = uow.vehiculos.guardar(vehiculo)
    uow.commit()
    return guardado


def sembrar_evento_de_alta(uow, id_vehiculo):
    alta = EventoHabilitacion(
        accion=ALTA,
        estado_anterior=None,
        estado_nuevo=PENDIENTE,
        motivo="Alta del vehiculo",
        id_operador=None,
        fecha=AHORA - timedelta(days=30),
    )
    uow.habilitaciones.registrar_evento_vehiculo(id_vehiculo, alta)
    uow.commit()
    return alta


def estado_guardado(uow, id_conductor, id_vehiculo):
    return uow.vehiculos.obtener(id_conductor, id_vehiculo).habilitacion


@pytest.mark.parametrize(
    ("estado_inicial", "accion", "estado_esperado"),
    [
        (estado, accion, nuevo)
        for (estado, accion), nuevo in TRANSICIONES_VALIDAS.items()
    ],
    ids=lambda valor: valor.name,
)
def test_aplica_las_transiciones_de_la_matriz_y_registra_el_evento(
    accionar, uow, estado_inicial, accion, estado_esperado
):
    conductor = sembrar_conductor(uow)
    vehiculo = sembrar_vehiculo(uow, conductor.id, estado_inicial)
    alta = sembrar_evento_de_alta(uow, vehiculo.id)

    resultado = accionar.ejecutar(
        id_conductor=conductor.id,
        id_vehiculo=vehiculo.id,
        accion=accion,
        motivo=MOTIVO,
        id_operador=ID_OPERADOR,
    )

    historial = uow.habilitaciones.historial_vehiculo(vehiculo.id)
    assert len(historial) == 2
    assert historial[0] == alta
    evento = historial[1]
    assert evento.accion is accion
    assert evento.estado_anterior is estado_inicial
    assert evento.estado_nuevo is estado_esperado
    assert evento.motivo == MOTIVO
    assert evento.id_operador == ID_OPERADOR
    assert evento.fecha == AHORA
    assert estado_guardado(uow, conductor.id, vehiculo.id) is estado_esperado
    assert resultado.id_vehiculo == vehiculo.id
    assert resultado.estado is estado_esperado
    assert resultado.eventos == [alta, evento]


@pytest.mark.parametrize(
    ("estado_inicial", "accion"),
    TRANSICIONES_NO_PERMITIDAS,
    ids=lambda valor: valor.name,
)
def test_transicion_no_permitida_lanza_error_y_no_persiste_nada(
    accionar, uow, estado_inicial, accion
):
    conductor = sembrar_conductor(uow)
    vehiculo = sembrar_vehiculo(uow, conductor.id, estado_inicial)
    alta = sembrar_evento_de_alta(uow, vehiculo.id)

    with pytest.raises(TransicionInvalida):
        accionar.ejecutar(
            id_conductor=conductor.id,
            id_vehiculo=vehiculo.id,
            accion=accion,
            motivo=MOTIVO,
            id_operador=ID_OPERADOR,
        )

    assert estado_guardado(uow, conductor.id, vehiculo.id) is estado_inicial
    assert uow.habilitaciones.historial_vehiculo(vehiculo.id) == [alta]


def test_aprobar_no_exige_licencia_ni_documentos_del_conductor(accionar, uow):
    conductor = sembrar_conductor(uow)
    vehiculo = sembrar_vehiculo(uow, conductor.id, PENDIENTE)
    assert uow.documentos.listar_por_conductor(conductor.id) == []

    resultado = accionar.ejecutar(
        id_conductor=conductor.id,
        id_vehiculo=vehiculo.id,
        accion=APROBAR,
        motivo=MOTIVO,
        id_operador=ID_OPERADOR,
    )

    assert resultado.estado is APROBADA


def test_suspender_y_luego_aprobar_quedan_ambos_en_el_historial_en_orden(
    accionar, uow, reloj
):
    conductor = sembrar_conductor(uow)
    vehiculo = sembrar_vehiculo(uow, conductor.id, APROBADA)

    accionar.ejecutar(
        id_conductor=conductor.id,
        id_vehiculo=vehiculo.id,
        accion=SUSPENDER,
        motivo="Revision de documentacion",
        id_operador=ID_OPERADOR,
    )
    reloj.avanzar(dias=1)
    resultado = accionar.ejecutar(
        id_conductor=conductor.id,
        id_vehiculo=vehiculo.id,
        accion=APROBAR,
        motivo="Documentacion regularizada",
        id_operador=ID_OPERADOR,
    )

    historial = uow.habilitaciones.historial_vehiculo(vehiculo.id)
    assert [(e.accion, e.estado_anterior, e.estado_nuevo) for e in historial] == [
        (SUSPENDER, APROBADA, SUSPENDIDA),
        (APROBAR, SUSPENDIDA, APROBADA),
    ]
    assert estado_guardado(uow, conductor.id, vehiculo.id) is APROBADA
    assert resultado.eventos == historial


@pytest.mark.parametrize("motivo", ["", "   "])
def test_motivo_vacio_lanza_datos_invalidos_y_no_persiste_nada(accionar, uow, motivo):
    conductor = sembrar_conductor(uow)
    vehiculo = sembrar_vehiculo(uow, conductor.id, PENDIENTE)
    alta = sembrar_evento_de_alta(uow, vehiculo.id)

    with pytest.raises(DatosInvalidos):
        accionar.ejecutar(
            id_conductor=conductor.id,
            id_vehiculo=vehiculo.id,
            accion=APROBAR,
            motivo=motivo,
            id_operador=ID_OPERADOR,
        )

    assert estado_guardado(uow, conductor.id, vehiculo.id) is PENDIENTE
    assert uow.habilitaciones.historial_vehiculo(vehiculo.id) == [alta]


@pytest.mark.parametrize(
    "caso",
    ["vehiculo_inexistente", "conductor_inexistente", "vehiculo_de_otro_conductor"],
)
def test_lanza_no_encontrado_y_no_persiste_nada(accionar, uow, caso):
    duenio = sembrar_conductor(uow, "30000001")
    otro = sembrar_conductor(uow, "30000002")
    vehiculo = sembrar_vehiculo(uow, duenio.id, PENDIENTE)
    alta = sembrar_evento_de_alta(uow, vehiculo.id)
    ids = {
        "vehiculo_inexistente": (duenio.id, vehiculo.id + 1),
        "conductor_inexistente": (otro.id + 1, vehiculo.id),
        "vehiculo_de_otro_conductor": (otro.id, vehiculo.id),
    }
    id_conductor, id_vehiculo = ids[caso]

    with pytest.raises(NoEncontrado):
        accionar.ejecutar(
            id_conductor=id_conductor,
            id_vehiculo=id_vehiculo,
            accion=APROBAR,
            motivo=MOTIVO,
            id_operador=ID_OPERADOR,
        )

    assert estado_guardado(uow, duenio.id, vehiculo.id) is PENDIENTE
    assert uow.habilitaciones.historial_vehiculo(vehiculo.id) == [alta]
    assert uow.habilitaciones.historial_vehiculo(vehiculo.id + 1) == []


def test_toma_el_vehiculo_con_bloqueo_de_fila_una_sola_vez(accionar, uow):
    conductor = sembrar_conductor(uow)
    vehiculo = sembrar_vehiculo(uow, conductor.id)

    accionar.ejecutar(
        id_conductor=conductor.id,
        id_vehiculo=vehiculo.id,
        accion=OBSERVAR,
        motivo=MOTIVO,
        id_operador=ID_OPERADOR,
    )

    assert uow.vehiculos_bloqueados == [(conductor.id, vehiculo.id)]


def test_el_historial_no_mezcla_eventos_de_otro_vehiculo_ni_del_conductor(
    accionar, uow
):
    conductor = sembrar_conductor(uow)
    vehiculo = sembrar_vehiculo(uow, conductor.id, patente="AAA111")
    otro_vehiculo = sembrar_vehiculo(uow, conductor.id, patente="BBB222")
    alta = sembrar_evento_de_alta(uow, vehiculo.id)
    sembrar_evento_de_alta(uow, otro_vehiculo.id)
    # el conductor tiene el mismo numero de id que el vehiculo: no deben confundirse
    uow.habilitaciones.registrar_evento_conductor(
        conductor.id,
        EventoHabilitacion(
            accion=ALTA,
            estado_anterior=None,
            estado_nuevo=PENDIENTE,
            motivo="Alta del conductor",
            id_operador=None,
            fecha=AHORA - timedelta(days=31),
        ),
    )
    uow.commit()

    resultado = accionar.ejecutar(
        id_conductor=conductor.id,
        id_vehiculo=vehiculo.id,
        accion=APROBAR,
        motivo=MOTIVO,
        id_operador=ID_OPERADOR,
    )

    assert len(resultado.eventos) == 2
    assert resultado.eventos[0] == alta
    assert len(uow.habilitaciones.historial_vehiculo(otro_vehiculo.id)) == 1
    assert len(uow.habilitaciones.historial_conductor(conductor.id)) == 1


def test_los_tipos_de_servicio_siguen_sin_habilitar_tras_aprobar(accionar, uow):
    conductor = sembrar_conductor(uow)
    vehiculo = sembrar_vehiculo(uow, conductor.id, PENDIENTE)

    accionar.ejecutar(
        id_conductor=conductor.id,
        id_vehiculo=vehiculo.id,
        accion=APROBAR,
        motivo=MOTIVO,
        id_operador=ID_OPERADOR,
    )

    guardado = uow.vehiculos.obtener(conductor.id, vehiculo.id)
    assert [s.habilitado for s in guardado.tipos_servicio] == [False, False]
