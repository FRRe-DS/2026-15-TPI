"""Caso de uso `listar_solicitudes_conductor` (GET /conductores/{id}/solicitudes).

Firmas bajo prueba:
    ListarSolicitudesConductor(uow: UnidadDeTrabajo, reloj: Reloj)
    ListarSolicitudesConductor.ejecutar(*, id_conductor, estado=None) -> list[Solicitud]

Devuelve todas las solicitudes del conductor en orden de alta. El `estado` de cada una es el
estado efectivo calculado con el `Reloj` (una `PENDIENTE` vencida figura `VENCIDA`) y el filtro
`estado` se aplica sobre ese estado efectivo. Lo guardado no se modifica. Lanza NoEncontrado si
el conductor no existe.
"""

from datetime import UTC, datetime, timedelta

import pytest
from app.aplicacion.casos_de_uso.listar_solicitudes_conductor import ListarSolicitudesConductor
from app.dominio.conductor import Conductor
from app.dominio.errores import NoEncontrado
from app.dominio.solicitud import EstadoSolicitud, Solicitud

from tests.unitarios.fakes.reloj_fijo import RelojFijo
from tests.unitarios.fakes.repositorios_en_memoria import UnidadDeTrabajoEnMemoria

AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
VIGENTE_HASTA = AHORA + timedelta(minutes=2)
VENCIDA_DESDE = AHORA - timedelta(minutes=2)

PENDIENTE = EstadoSolicitud.PENDIENTE
ACEPTADO = EstadoSolicitud.ACEPTADO
RECHAZADO = EstadoSolicitud.RECHAZADO
VENCIDA = EstadoSolicitud.VENCIDA


@pytest.fixture
def uow():
    return UnidadDeTrabajoEnMemoria()


@pytest.fixture
def listar(uow):
    return ListarSolicitudesConductor(uow, RelojFijo(AHORA))


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


def sembrar_solicitud(uow, id_conductor, vence_en=VIGENTE_HASTA, estado=PENDIENTE):
    solicitud = Solicitud(id_conductor=id_conductor, vence_en=vence_en, estado=estado)
    guardada = uow.solicitudes.guardar(solicitud)
    uow.commit()
    return guardada


def ids_de(solicitudes):
    return [solicitud.id for solicitud in solicitudes]


def test_devuelve_solo_las_solicitudes_del_conductor(uow, listar):
    ana = sembrar_conductor(uow)
    beto = sembrar_conductor(uow, dni="30123457")
    de_ana = sembrar_solicitud(uow, ana.id)
    sembrar_solicitud(uow, beto.id)

    resultado = listar.ejecutar(id_conductor=ana.id)

    assert ids_de(resultado) == [de_ana.id]


def test_conserva_el_orden_de_alta(uow, listar):
    conductor = sembrar_conductor(uow)
    primera = sembrar_solicitud(uow, conductor.id)
    segunda = sembrar_solicitud(uow, conductor.id, estado=RECHAZADO)
    tercera = sembrar_solicitud(uow, conductor.id)

    resultado = listar.ejecutar(id_conductor=conductor.id)

    assert ids_de(resultado) == [primera.id, segunda.id, tercera.id]


def test_conductor_sin_solicitudes_devuelve_lista_vacia(uow, listar):
    conductor = sembrar_conductor(uow)

    assert listar.ejecutar(id_conductor=conductor.id) == []


def test_una_pendiente_vencida_figura_como_vencida(uow, listar):
    conductor = sembrar_conductor(uow)
    solicitud = sembrar_solicitud(uow, conductor.id, vence_en=VENCIDA_DESDE)

    [resultado] = listar.ejecutar(id_conductor=conductor.id)

    assert resultado.id == solicitud.id
    assert resultado.estado is VENCIDA


def test_una_pendiente_vigente_sigue_pendiente(uow, listar):
    conductor = sembrar_conductor(uow)
    sembrar_solicitud(uow, conductor.id, vence_en=VIGENTE_HASTA)

    [resultado] = listar.ejecutar(id_conductor=conductor.id)

    assert resultado.estado is PENDIENTE


@pytest.mark.parametrize("estado_respondido", [ACEPTADO, RECHAZADO])
def test_una_respondida_conserva_su_estado_aunque_haya_pasado_su_vencimiento(
    uow, listar, estado_respondido
):
    conductor = sembrar_conductor(uow)
    sembrar_solicitud(uow, conductor.id, vence_en=VENCIDA_DESDE, estado=estado_respondido)

    [resultado] = listar.ejecutar(id_conductor=conductor.id)

    assert resultado.estado is estado_respondido


def test_calcular_el_estado_efectivo_no_modifica_lo_guardado(uow, listar):
    conductor = sembrar_conductor(uow)
    solicitud = sembrar_solicitud(uow, conductor.id, vence_en=VENCIDA_DESDE)

    listar.ejecutar(id_conductor=conductor.id)

    assert uow.solicitudes.obtener(solicitud.id).estado is PENDIENTE


def sembrar_una_de_cada_estado_efectivo(uow, id_conductor):
    return {
        PENDIENTE: sembrar_solicitud(uow, id_conductor, vence_en=VIGENTE_HASTA),
        VENCIDA: sembrar_solicitud(uow, id_conductor, vence_en=VENCIDA_DESDE),
        ACEPTADO: sembrar_solicitud(uow, id_conductor, estado=ACEPTADO),
        RECHAZADO: sembrar_solicitud(uow, id_conductor, estado=RECHAZADO),
    }


@pytest.mark.parametrize("estado_pedido", [PENDIENTE, VENCIDA, ACEPTADO, RECHAZADO])
def test_el_filtro_estado_devuelve_solo_las_de_ese_estado_efectivo(uow, listar, estado_pedido):
    conductor = sembrar_conductor(uow)
    sembradas = sembrar_una_de_cada_estado_efectivo(uow, conductor.id)

    resultado = listar.ejecutar(id_conductor=conductor.id, estado=estado_pedido)

    assert ids_de(resultado) == [sembradas[estado_pedido].id]


def test_filtrar_pendiente_excluye_a_la_pendiente_vencida(uow, listar):
    conductor = sembrar_conductor(uow)
    sembrar_solicitud(uow, conductor.id, vence_en=VENCIDA_DESDE)

    assert listar.ejecutar(id_conductor=conductor.id, estado=PENDIENTE) == []


def test_filtrar_vencida_incluye_a_la_pendiente_vencida(uow, listar):
    conductor = sembrar_conductor(uow)
    vencida = sembrar_solicitud(uow, conductor.id, vence_en=VENCIDA_DESDE)

    resultado = listar.ejecutar(id_conductor=conductor.id, estado=VENCIDA)

    assert ids_de(resultado) == [vencida.id]


def test_sin_filtro_devuelve_todas_las_solicitudes(uow, listar):
    conductor = sembrar_conductor(uow)
    sembradas = sembrar_una_de_cada_estado_efectivo(uow, conductor.id)

    resultado = listar.ejecutar(id_conductor=conductor.id)

    assert len(resultado) == len(sembradas)


def test_conductor_inexistente_lanza_no_encontrado(listar):
    with pytest.raises(NoEncontrado):
        listar.ejecutar(id_conductor=999)
