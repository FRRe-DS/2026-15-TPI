"""`SqlRepositorioSolicitudes(session)`: el puerto `RepositorioSolicitudes` sobre PostgreSQL.

Diseno que fijan los tests (igual que el fake `RepositorioSolicitudesEnMemoria`):
- `guardar` sin id inserta la solicitud con `estado`, `vence_en`, `respuesta` y `hora_rta`,
  le asigna id y hace `flush` (no `commit`: lo decide la unidad de trabajo); con id
  actualiza la fila existente.
- `obtener` devuelve la solicitud de dominio o `None`.
- `listar_por_conductor` devuelve solo las del conductor, en orden de alta (id ascendente).
- La base es la ultima defensa: `respuesta` y `hora_rta` van juntas y `estado` coincide con
  `respuesta` (`CHECK`).
- `bloquear_solicitud` usa `SELECT ... FOR UPDATE` con `populate_existing`: si la sesion ya
  tenia la fila cargada, devuelve lo que otra transaccion confirmo mientras tanto, no la
  copia vieja. El test retiene la referencia a la fila ORM a proposito (sin retenerla,
  SQLAlchemy usa una referencia debil y el test podria pasar sin `populate_existing`).
Las lecturas de verificacion se hacen desde una sesion nueva.
"""

from datetime import UTC, datetime, timedelta

import pytest
from app.dominio.solicitud import EstadoSolicitud, Solicitud
from app.infraestructura.db.modelos import Conductor as ConductorOrm
from app.infraestructura.db.modelos import Solicitud as SolicitudOrm
from app.infraestructura.repositorios.sql_solicitudes import SqlRepositorioSolicitudes
from app.infraestructura.repositorios.sql_unidad_de_trabajo import SqlUnidadDeTrabajo
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError

AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
VENCE_EN = AHORA + timedelta(minutes=2)
HORA_RTA = AHORA - timedelta(seconds=30)
HORA_RTA_DE_LA_OTRA_TRANSACCION = AHORA - timedelta(seconds=45)

PENDIENTE = EstadoSolicitud.PENDIENTE
ACEPTADO = EstadoSolicitud.ACEPTADO
RECHAZADO = EstadoSolicitud.RECHAZADO
VENCIDA = EstadoSolicitud.VENCIDA


@pytest.fixture
def repositorio(sesion_bd):
    return SqlRepositorioSolicitudes(sesion_bd)


@pytest.fixture
def uow(fabrica_sesiones, sesion_bd):
    """Depende de `sesion_bd` para que la base se limpie al terminar cada prueba."""
    return SqlUnidadDeTrabajo(fabrica_sesiones)


def sembrar_conductor(sesion, dni="30123456"):
    fila = ConductorOrm(
        dni=dni,
        nombre="Ana",
        apellido="Perez",
        telefono="+54 379 4000000",
        email="ana@example.com",
    )
    sesion.add(fila)
    sesion.flush()
    return fila.id_conductor


def nueva_solicitud(id_conductor, estado=PENDIENTE, id_viaje=None):
    """Arma una solicitud coherente con el `CHECK`: respuesta y hora solo si fue respondida."""
    respondida = estado in (ACEPTADO, RECHAZADO)
    return Solicitud(
        id_conductor=id_conductor,
        vence_en=VENCE_EN,
        id_viaje=id_viaje,
        estado=estado,
        respuesta=estado if respondida else None,
        hora_rta=HORA_RTA if respondida else None,
    )


def leer_desde_otra_sesion(fabrica_sesiones, id_solicitud):
    with fabrica_sesiones() as otra_sesion:
        return SqlRepositorioSolicitudes(otra_sesion).obtener(id_solicitud)


def responder_en_otra_transaccion(fabrica_sesiones, id_solicitud):
    """Otra transaccion acepta la solicitud y la confirma."""
    with fabrica_sesiones() as otra_sesion:
        otra_sesion.execute(
            text(
                """
                UPDATE solicitud
                SET estado = 'ACEPTADO', respuesta = 'ACEPTADO', hora_rta = :hora
                WHERE id_solicitud = :id
                """
            ),
            {"id": id_solicitud, "hora": HORA_RTA_DE_LA_OTRA_TRANSACCION},
        )
        otra_sesion.commit()


# --- guardar y obtener ---


@pytest.mark.parametrize("estado", [PENDIENTE, ACEPTADO, RECHAZADO, VENCIDA])
def test_guardar_y_obtener_persisten_estado_vence_en_respuesta_y_hora(
    repositorio, sesion_bd, fabrica_sesiones, estado
):
    id_conductor = sembrar_conductor(sesion_bd)

    guardada = repositorio.guardar(nueva_solicitud(id_conductor, estado, id_viaje=42))
    sesion_bd.commit()

    leida = leer_desde_otra_sesion(fabrica_sesiones, guardada.id)

    assert isinstance(leida, Solicitud)
    assert leida.id == guardada.id
    assert leida.id_conductor == id_conductor
    assert leida.id_viaje == 42
    assert leida.estado is estado
    assert leida.vence_en == VENCE_EN
    if estado in (ACEPTADO, RECHAZADO):
        assert leida.respuesta is estado
        assert leida.hora_rta == HORA_RTA
    else:
        assert leida.respuesta is None
        assert leida.hora_rta is None


def test_guardar_sin_id_asigna_ids_incrementales(repositorio, sesion_bd):
    id_conductor = sembrar_conductor(sesion_bd)

    primera = repositorio.guardar(nueva_solicitud(id_conductor))
    segunda = repositorio.guardar(nueva_solicitud(id_conductor))

    assert (primera.id, segunda.id) == (1, 2)


def test_guardar_una_solicitud_con_id_actualiza_sin_duplicar_filas(
    repositorio, sesion_bd, fabrica_sesiones
):
    id_conductor = sembrar_conductor(sesion_bd)
    solicitud = repositorio.guardar(nueva_solicitud(id_conductor))
    sesion_bd.commit()
    solicitud.estado = ACEPTADO
    solicitud.respuesta = ACEPTADO
    solicitud.hora_rta = HORA_RTA

    repositorio.guardar(solicitud)
    sesion_bd.commit()

    assert sesion_bd.execute(text("SELECT count(*) FROM solicitud")).scalar_one() == 1
    leida = leer_desde_otra_sesion(fabrica_sesiones, solicitud.id)
    assert leida.estado is ACEPTADO
    assert leida.respuesta is ACEPTADO
    assert leida.hora_rta == HORA_RTA


def test_obtener_una_solicitud_inexistente_devuelve_none(repositorio):
    assert repositorio.obtener(999) is None


# --- listar por conductor ---


def test_listar_por_conductor_devuelve_solo_las_suyas_en_orden_de_alta(
    repositorio, sesion_bd, fabrica_sesiones
):
    duenio = sembrar_conductor(sesion_bd, "30000001")
    otro = sembrar_conductor(sesion_bd, "30000002")
    primera = repositorio.guardar(nueva_solicitud(duenio))
    repositorio.guardar(nueva_solicitud(otro))
    tercera = repositorio.guardar(nueva_solicitud(duenio, ACEPTADO, id_viaje=7))
    sesion_bd.commit()

    with fabrica_sesiones() as otra_sesion:
        resultado = SqlRepositorioSolicitudes(otra_sesion).listar_por_conductor(duenio)

    assert [s.id for s in resultado] == [primera.id, tercera.id]
    assert [s.id_conductor for s in resultado] == [duenio, duenio]
    assert [s.estado for s in resultado] == [PENDIENTE, ACEPTADO]


def test_listar_por_conductor_sin_solicitudes_o_inexistente_devuelve_lista_vacia(repositorio):
    assert repositorio.listar_por_conductor(999) == []


# --- la base rechaza combinaciones incoherentes (CHECK) ---


@pytest.mark.parametrize(
    "actualizacion",
    [
        pytest.param(
            "SET estado = 'ACEPTADO', respuesta = 'ACEPTADO'",
            id="respuesta_sin_hora",
        ),
        pytest.param("SET hora_rta = :hora", id="hora_sin_respuesta"),
        pytest.param(
            "SET estado = 'ACEPTADO', respuesta = 'RECHAZADO', hora_rta = :hora",
            id="estado_no_coincide_con_respuesta",
        ),
        pytest.param("SET estado = 'ACEPTADO'", id="estado_respondido_sin_respuesta"),
    ],
)
def test_la_base_rechaza_respuestas_incoherentes(repositorio, sesion_bd, actualizacion):
    id_conductor = sembrar_conductor(sesion_bd)
    guardada = repositorio.guardar(nueva_solicitud(id_conductor))
    sesion_bd.commit()

    with pytest.raises(IntegrityError):
        sesion_bd.execute(
            text(f"UPDATE solicitud {actualizacion} WHERE id_solicitud = :id"),
            {"id": guardada.id, "hora": HORA_RTA},
        )
    sesion_bd.rollback()


def test_la_base_rechaza_un_estado_fuera_del_enum(repositorio, sesion_bd):
    id_conductor = sembrar_conductor(sesion_bd)
    guardada = repositorio.guardar(nueva_solicitud(id_conductor))
    sesion_bd.commit()

    with pytest.raises(IntegrityError):
        sesion_bd.execute(
            text("UPDATE solicitud SET estado = 'VOLANDO' WHERE id_solicitud = :id"),
            {"id": guardada.id},
        )
    sesion_bd.rollback()


# --- bloqueo de fila ---


def test_bloquear_solicitud_devuelve_la_solicitud_de_dominio_o_none(uow, sesion_bd):
    id_conductor = sembrar_conductor(sesion_bd)
    guardada = SqlRepositorioSolicitudes(sesion_bd).guardar(nueva_solicitud(id_conductor))
    sesion_bd.commit()

    with uow:
        bloqueada = uow.bloquear_solicitud(guardada.id)
        inexistente = uow.bloquear_solicitud(999)

    assert isinstance(bloqueada, Solicitud)
    assert (bloqueada.id, bloqueada.id_conductor) == (guardada.id, id_conductor)
    assert inexistente is None


def test_bloquear_solicitud_devuelve_lo_confirmado_aunque_la_sesion_la_tenga_cargada(
    uow, sesion_bd, fabrica_sesiones
):
    """Si falta `populate_existing`, devuelve la copia vieja de la sesion y este test falla."""
    id_conductor = sembrar_conductor(sesion_bd)
    guardada = SqlRepositorioSolicitudes(sesion_bd).guardar(nueva_solicitud(id_conductor))
    sesion_bd.commit()

    with uow:
        # Se carga y se retiene la fila ORM en la sesion de la transaccion.
        fila = uow._sesion.get(SolicitudOrm, guardada.id)
        assert fila is not None
        assert fila.estado == "PENDIENTE"

        responder_en_otra_transaccion(fabrica_sesiones, guardada.id)

        bloqueada = uow.bloquear_solicitud(guardada.id)

        # La referencia viva se refresco con la version confirmada por la otra transaccion.
        assert fila.estado == "ACEPTADO"

    assert bloqueada.estado is ACEPTADO
    assert bloqueada.respuesta is ACEPTADO
    assert bloqueada.hora_rta == HORA_RTA_DE_LA_OTRA_TRANSACCION


def test_el_sql_emitido_al_bloquear_una_solicitud_contiene_for_update(
    uow, sesion_bd, engine_integracion
):
    id_conductor = sembrar_conductor(sesion_bd)
    guardada = SqlRepositorioSolicitudes(sesion_bd).guardar(nueva_solicitud(id_conductor))
    sesion_bd.commit()
    sentencias = []

    def registrar(conexion, cursor, sentencia, parametros, contexto, ejecutar_muchos):
        sentencias.append(sentencia.upper())

    event.listen(engine_integracion, "before_cursor_execute", registrar)
    try:
        with uow:
            uow.bloquear_solicitud(guardada.id)
    finally:
        event.remove(engine_integracion, "before_cursor_execute", registrar)

    assert any("FOR UPDATE" in sentencia for sentencia in sentencias)
