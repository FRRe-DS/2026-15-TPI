"""Caso de uso `actualizar_estado_conductor` (PATCH /conductores/{id}/estado).

Firmas bajo prueba:
    ActualizarEstadoConductor(uow: UnidadDeTrabajo, reloj: Reloj, *,
                              latitud_simulada: float, longitud_simulada: float)
    ActualizarEstadoConductor.ejecutar(*, id_conductor, estado=None,
                                       id_vehiculo_activo=NO_INFORMADO,
                                       latitud=None, longitud=None) -> EstadoDelConductor

`estado=None`, `latitud=None` y `longitud=None` significan "no informado". Para
`id_vehiculo_activo`, `NO_INFORMADO` (de `app.dominio.disponibilidad`) es "no informado" y
`None` quita el vehiculo activo. Las reglas del estado son las de `disponibilidad.py`; aca se
prueba el caso de uso: bloqueo del conductor, vehiculo activo propio, ubicacion y persistencia.
"""

import copy
from datetime import UTC, datetime, timedelta

import pytest
from app.aplicacion.casos_de_uso.actualizar_estado_conductor import ActualizarEstadoConductor
from app.dominio.conductor import Conductor, EstadoConductor
from app.dominio.errores import ConductorNoHabilitado, DatosInvalidos, NoEncontrado
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.vehiculo import TipoServicio, TipoVehiculo, Vehiculo

from tests.unitarios.fakes.reloj_fijo import RelojFijo
from tests.unitarios.fakes.repositorios_en_memoria import UnidadDeTrabajoEnMemoria

AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
ULTIMO_CAMBIO = AHORA - timedelta(days=3)
FECHA_UBICACION_PREVIA = AHORA - timedelta(days=2)
LATITUD_SIMULADA = -27.4511
LONGITUD_SIMULADA = -58.9867
LATITUD_PREVIA = -34.6037
LONGITUD_PREVIA = -58.3816
LATITUD_PEDIDA = -31.4201
LONGITUD_PEDIDA = -64.1888

DESCONECTADO = EstadoConductor.DESCONECTADO
CONECTADO = EstadoConductor.CONECTADO
DISPONIBLE = EstadoConductor.DISPONIBLE
OCUPADO = EstadoConductor.OCUPADO
APROBADA = EstadoHabilitacion.APROBADA
PENDIENTE = EstadoHabilitacion.PENDIENTE


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
def actualizar(uow):
    return ActualizarEstadoConductor(
        uow,
        RelojFijo(AHORA),
        latitud_simulada=LATITUD_SIMULADA,
        longitud_simulada=LONGITUD_SIMULADA,
    )


def sembrar_conductor(uow, dni="30123456", **atributos):
    conductor = Conductor.crear(
        dni=dni,
        nombre="Ana",
        apellido="Perez",
        telefono="+54 379 4000000",
        email="ana@example.com",
    )
    conductor.habilitacion = APROBADA
    conductor.fecha_ultimo_cambio_estado = ULTIMO_CAMBIO
    for atributo, valor in atributos.items():
        setattr(conductor, atributo, valor)
    guardado = uow.conductores.guardar(conductor)
    uow.commit()
    return guardado


def sembrar_vehiculo(uow, id_conductor, habilitacion=APROBADA, patente="AB123CD"):
    vehiculo = Vehiculo.crear(
        tipo=TipoVehiculo.AUTO,
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


def sembrar_conductor_con_vehiculo_activo(uow, estado=CONECTADO, **atributos):
    conductor = sembrar_conductor(uow, estado=estado, **atributos)
    vehiculo = sembrar_vehiculo(uow, conductor.id)
    conductor.id_vehiculo_activo = vehiculo.id
    uow.commit()
    return conductor, vehiculo


def guardado(uow, id_conductor):
    return uow.conductores.obtener(id_conductor)


def copia_guardada(uow, id_conductor):
    return copy.deepcopy(guardado(uow, id_conductor))


@pytest.mark.parametrize("estado_inicial", [DESCONECTADO, CONECTADO, OCUPADO])
def test_pedir_disponible_cumpliendo_la_regla_lo_deja_disponible(uow, actualizar, estado_inicial):
    conductor, vehiculo = sembrar_conductor_con_vehiculo_activo(uow, estado_inicial)

    resultado = actualizar.ejecutar(id_conductor=conductor.id, estado=DISPONIBLE)

    assert resultado.id_conductor == conductor.id
    assert resultado.estado is DISPONIBLE
    assert resultado.id_vehiculo_activo == vehiculo.id
    assert resultado.actualizado == AHORA
    assert guardado(uow, conductor.id).estado is DISPONIBLE
    assert guardado(uow, conductor.id).fecha_ultimo_cambio_estado == AHORA


def test_acepta_el_estado_como_texto(uow, actualizar):
    conductor, _ = sembrar_conductor_con_vehiculo_activo(uow, CONECTADO)

    resultado = actualizar.ejecutar(id_conductor=conductor.id, estado="DISPONIBLE")

    assert resultado.estado is DISPONIBLE


@pytest.mark.parametrize(
    "caso", ["conductor_no_aprobado", "vehiculo_no_aprobado", "sin_vehiculo_activo"]
)
def test_pedir_disponible_sin_cumplir_la_regla_lanza_error_y_no_cambia_nada(uow, actualizar, caso):
    conductor = sembrar_conductor(
        uow,
        estado=CONECTADO,
        habilitacion=PENDIENTE if caso == "conductor_no_aprobado" else APROBADA,
    )
    if caso != "sin_vehiculo_activo":
        habilitacion = PENDIENTE if caso == "vehiculo_no_aprobado" else APROBADA
        conductor.id_vehiculo_activo = sembrar_vehiculo(uow, conductor.id, habilitacion).id
        uow.commit()
    antes = copia_guardada(uow, conductor.id)

    with pytest.raises(ConductorNoHabilitado):
        actualizar.ejecutar(id_conductor=conductor.id, estado=DISPONIBLE)

    assert guardado(uow, conductor.id) == antes


@pytest.mark.parametrize("estado_pedido", [DESCONECTADO, CONECTADO])
@pytest.mark.parametrize("estado_inicial", [DESCONECTADO, CONECTADO, DISPONIBLE, OCUPADO])
def test_desconectado_y_conectado_se_aceptan_siempre(
    uow, actualizar, estado_inicial, estado_pedido
):
    conductor = sembrar_conductor(uow, estado=estado_inicial, habilitacion=PENDIENTE)

    resultado = actualizar.ejecutar(id_conductor=conductor.id, estado=estado_pedido)

    assert resultado.estado is estado_pedido
    assert guardado(uow, conductor.id).estado is estado_pedido


def test_pedir_ocupado_lanza_datos_invalidos_y_no_cambia_nada(uow, actualizar):
    conductor, _ = sembrar_conductor_con_vehiculo_activo(uow, DISPONIBLE)
    antes = copia_guardada(uow, conductor.id)

    with pytest.raises(DatosInvalidos):
        actualizar.ejecutar(id_conductor=conductor.id, estado=OCUPADO)

    assert guardado(uow, conductor.id) == antes


def test_latitud_y_longitud_guardan_la_ubicacion_con_la_hora_del_reloj(uow, actualizar):
    conductor = sembrar_conductor(uow, estado=CONECTADO)

    actualizar.ejecutar(id_conductor=conductor.id, latitud=LATITUD_PEDIDA, longitud=LONGITUD_PEDIDA)

    persistido = guardado(uow, conductor.id)
    assert persistido.latitud == LATITUD_PEDIDA
    assert persistido.longitud == LONGITUD_PEDIDA
    assert persistido.fecha_act_ubic == AHORA


def test_actualizar_solo_la_ubicacion_no_cambia_la_fecha_del_estado(uow, actualizar):
    conductor = sembrar_conductor(uow, estado=CONECTADO)

    resultado = actualizar.ejecutar(
        id_conductor=conductor.id, latitud=LATITUD_PEDIDA, longitud=LONGITUD_PEDIDA
    )

    assert resultado.estado is CONECTADO
    assert resultado.actualizado == ULTIMO_CAMBIO
    assert guardado(uow, conductor.id).fecha_ultimo_cambio_estado == ULTIMO_CAMBIO


@pytest.mark.parametrize(
    "coordenadas",
    [{"latitud": LATITUD_PEDIDA}, {"longitud": LONGITUD_PEDIDA}],
    ids=["solo_latitud", "solo_longitud"],
)
def test_una_sola_coordenada_lanza_datos_invalidos_y_no_cambia_nada(uow, actualizar, coordenadas):
    conductor = sembrar_conductor(uow, estado=CONECTADO)
    antes = copia_guardada(uow, conductor.id)

    with pytest.raises(DatosInvalidos):
        actualizar.ejecutar(id_conductor=conductor.id, estado=DESCONECTADO, **coordenadas)

    assert guardado(uow, conductor.id) == antes


@pytest.mark.parametrize(
    "coordenadas",
    [
        {"latitud": 91.0, "longitud": LONGITUD_PEDIDA},
        {"latitud": LATITUD_PEDIDA, "longitud": 181.0},
    ],
    ids=["latitud_fuera_de_rango", "longitud_fuera_de_rango"],
)
def test_coordenada_fuera_de_rango_lanza_datos_invalidos_y_no_cambia_nada(
    uow, actualizar, coordenadas
):
    conductor = sembrar_conductor(uow, estado=CONECTADO)
    antes = copia_guardada(uow, conductor.id)

    with pytest.raises(DatosInvalidos):
        actualizar.ejecutar(id_conductor=conductor.id, estado=DESCONECTADO, **coordenadas)

    assert guardado(uow, conductor.id) == antes


def test_sin_ubicacion_en_el_pedido_no_cambia_la_ubicacion_previa(uow, actualizar):
    conductor = sembrar_conductor(
        uow,
        estado=CONECTADO,
        latitud=LATITUD_PREVIA,
        longitud=LONGITUD_PREVIA,
        fecha_act_ubic=FECHA_UBICACION_PREVIA,
    )

    actualizar.ejecutar(id_conductor=conductor.id, estado=DESCONECTADO)

    persistido = guardado(uow, conductor.id)
    assert persistido.latitud == LATITUD_PREVIA
    assert persistido.longitud == LONGITUD_PREVIA
    assert persistido.fecha_act_ubic == FECHA_UBICACION_PREVIA


def test_un_cuerpo_sin_ningun_campo_lanza_datos_invalidos_y_no_cambia_nada(uow, actualizar):
    conductor = sembrar_conductor(uow, estado=CONECTADO)
    antes = copia_guardada(uow, conductor.id)

    with pytest.raises(DatosInvalidos):
        actualizar.ejecutar(id_conductor=conductor.id)

    assert guardado(uow, conductor.id) == antes


def test_conductor_inexistente_lanza_no_encontrado(uow, actualizar):
    conductor = sembrar_conductor(uow)

    with pytest.raises(NoEncontrado):
        actualizar.ejecutar(id_conductor=conductor.id + 1, estado=CONECTADO)


@pytest.mark.parametrize("caso", ["inexistente", "de_otro_conductor"])
def test_vehiculo_activo_ajeno_o_inexistente_lanza_no_encontrado_y_no_cambia_nada(
    uow, actualizar, caso
):
    conductor = sembrar_conductor(uow, "30000001", estado=CONECTADO)
    otro = sembrar_conductor(uow, "30000002", estado=CONECTADO)
    vehiculo_ajeno = sembrar_vehiculo(uow, otro.id)
    id_vehiculo = vehiculo_ajeno.id if caso == "de_otro_conductor" else vehiculo_ajeno.id + 100
    antes = copia_guardada(uow, conductor.id)

    with pytest.raises(NoEncontrado):
        actualizar.ejecutar(
            id_conductor=conductor.id, estado=DISPONIBLE, id_vehiculo_activo=id_vehiculo
        )

    assert guardado(uow, conductor.id) == antes
    assert guardado(uow, otro.id).id_vehiculo_activo is None


def test_informar_un_vehiculo_propio_lo_deja_activo_y_cambia_la_fecha(uow, actualizar):
    conductor = sembrar_conductor(uow, estado=CONECTADO)
    vehiculo = sembrar_vehiculo(uow, conductor.id)

    resultado = actualizar.ejecutar(
        id_conductor=conductor.id, estado=DISPONIBLE, id_vehiculo_activo=vehiculo.id
    )

    assert resultado.estado is DISPONIBLE
    assert resultado.id_vehiculo_activo == vehiculo.id
    assert guardado(uow, conductor.id).id_vehiculo_activo == vehiculo.id


def test_null_quita_el_vehiculo_activo_y_baja_a_conectado_al_conductor_disponible(uow, actualizar):
    conductor, _ = sembrar_conductor_con_vehiculo_activo(uow, DISPONIBLE)

    resultado = actualizar.ejecutar(id_conductor=conductor.id, id_vehiculo_activo=None)

    assert resultado.estado is CONECTADO
    assert resultado.id_vehiculo_activo is None
    assert resultado.actualizado == AHORA
    assert guardado(uow, conductor.id).id_vehiculo_activo is None


def test_null_en_un_conductor_que_no_estaba_disponible_conserva_su_estado(uow, actualizar):
    conductor, _ = sembrar_conductor_con_vehiculo_activo(uow, CONECTADO)

    resultado = actualizar.ejecutar(id_conductor=conductor.id, id_vehiculo_activo=None)

    assert resultado.estado is CONECTADO
    assert resultado.id_vehiculo_activo is None
    assert resultado.actualizado == AHORA


def test_un_pedido_que_no_cambia_nada_conserva_la_fecha_del_ultimo_cambio(uow, actualizar):
    conductor, vehiculo = sembrar_conductor_con_vehiculo_activo(uow, CONECTADO)

    resultado = actualizar.ejecutar(
        id_conductor=conductor.id, estado=CONECTADO, id_vehiculo_activo=vehiculo.id
    )

    assert resultado.actualizado == ULTIMO_CAMBIO
    assert guardado(uow, conductor.id).fecha_ultimo_cambio_estado == ULTIMO_CAMBIO


def test_bloquea_al_conductor_con_bloquear_conductor_una_sola_vez(uow, actualizar):
    conductor = sembrar_conductor(uow, estado=CONECTADO)

    actualizar.ejecutar(id_conductor=conductor.id, estado=DESCONECTADO)

    assert uow.conductores_bloqueados == [conductor.id]


def test_un_error_no_deja_cambios_a_medias_aunque_la_ubicacion_sea_valida(uow, actualizar):
    conductor = sembrar_conductor(uow, estado=CONECTADO, habilitacion=PENDIENTE)
    antes = copia_guardada(uow, conductor.id)

    with pytest.raises(ConductorNoHabilitado):
        actualizar.ejecutar(
            id_conductor=conductor.id,
            estado=DISPONIBLE,
            latitud=LATITUD_PEDIDA,
            longitud=LONGITUD_PEDIDA,
        )

    assert guardado(uow, conductor.id) == antes


# --- Ubicacion simulada ---


@pytest.mark.parametrize("estado_pedido", [CONECTADO, DISPONIBLE])
def test_al_salir_de_desconectado_sin_ubicacion_previa_ni_pedida_asigna_la_simulada(
    uow, actualizar, estado_pedido
):
    conductor, _ = sembrar_conductor_con_vehiculo_activo(uow, DESCONECTADO)

    actualizar.ejecutar(id_conductor=conductor.id, estado=estado_pedido)

    persistido = guardado(uow, conductor.id)
    assert persistido.latitud == LATITUD_SIMULADA
    assert persistido.longitud == LONGITUD_SIMULADA
    assert persistido.fecha_act_ubic == AHORA


def test_si_ya_tiene_ubicacion_la_simulada_no_la_cambia(uow, actualizar):
    conductor = sembrar_conductor(
        uow,
        estado=DESCONECTADO,
        latitud=LATITUD_PREVIA,
        longitud=LONGITUD_PREVIA,
        fecha_act_ubic=FECHA_UBICACION_PREVIA,
    )

    actualizar.ejecutar(id_conductor=conductor.id, estado=CONECTADO)

    persistido = guardado(uow, conductor.id)
    assert persistido.latitud == LATITUD_PREVIA
    assert persistido.longitud == LONGITUD_PREVIA
    assert persistido.fecha_act_ubic == FECHA_UBICACION_PREVIA


def test_si_el_pedido_trae_coordenadas_usa_esas_y_no_la_simulada(uow, actualizar):
    conductor = sembrar_conductor(uow, estado=DESCONECTADO)

    actualizar.ejecutar(
        id_conductor=conductor.id,
        estado=CONECTADO,
        latitud=LATITUD_PEDIDA,
        longitud=LONGITUD_PEDIDA,
    )

    persistido = guardado(uow, conductor.id)
    assert persistido.latitud == LATITUD_PEDIDA
    assert persistido.longitud == LONGITUD_PEDIDA
    assert persistido.fecha_act_ubic == AHORA


def test_sin_cambiar_de_desconectado_no_asigna_la_ubicacion_simulada(uow, actualizar):
    conductor = sembrar_conductor(uow, estado=DESCONECTADO)

    actualizar.ejecutar(id_conductor=conductor.id, estado=DESCONECTADO)

    persistido = guardado(uow, conductor.id)
    assert persistido.latitud is None
    assert persistido.longitud is None
    assert persistido.fecha_act_ubic is None


def test_si_no_sale_de_desconectado_por_un_error_no_queda_la_ubicacion_simulada(uow, actualizar):
    conductor = sembrar_conductor(uow, estado=DESCONECTADO, habilitacion=PENDIENTE)

    with pytest.raises(ConductorNoHabilitado):
        actualizar.ejecutar(id_conductor=conductor.id, estado=DISPONIBLE)

    assert guardado(uow, conductor.id).latitud is None


def test_desde_conectado_sin_ubicacion_no_se_asigna_la_simulada(uow, actualizar):
    conductor = sembrar_conductor(uow, estado=CONECTADO)

    actualizar.ejecutar(id_conductor=conductor.id, estado=DESCONECTADO)

    assert guardado(uow, conductor.id).latitud is None


def test_la_ubicacion_simulada_asignada_nunca_es_cero_cero(uow, actualizar):
    conductor = sembrar_conductor(uow, estado=DESCONECTADO)

    actualizar.ejecutar(id_conductor=conductor.id, estado=CONECTADO)

    persistido = guardado(uow, conductor.id)
    assert (persistido.latitud, persistido.longitud) != (0.0, 0.0)


def test_no_se_puede_construir_con_la_coordenada_cero_cero(uow):
    with pytest.raises(ValueError, match="0, 0"):
        ActualizarEstadoConductor(
            uow, RelojFijo(AHORA), latitud_simulada=0.0, longitud_simulada=0.0
        )
