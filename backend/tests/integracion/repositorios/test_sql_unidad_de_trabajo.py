"""`SqlUnidadDeTrabajo(fabrica_sesiones)`: el puerto `UnidadDeTrabajo` sobre PostgreSQL.

Diseno que fijan los tests (igual que el fake `UnidadDeTrabajoEnMemoria`):
- Se construye con un `sessionmaker`. Cada `with uow:` abre una Session NUEVA y crea sobre
  ella los 4 repositorios SQL, accesibles como atributos dentro del `with`; el mismo objeto
  `uow` se puede reusar en varios `with` consecutivos.
- `commit()` confirma; `rollback()` descarta lo pendiente y la uow sigue usable. Al salir
  del `with` se descarta lo no confirmado (con o sin excepcion, que se propaga) y se cierra
  la sesion.
- `bloquear_conductor(id)` y `bloquear_vehiculo(id_conductor, id_vehiculo)` devuelven la
  entidad de dominio (o None) con `SELECT ... FOR UPDATE`. El bloqueo se prueba sin sleeps:
  una segunda sesion intenta `FOR UPDATE NOWAIT` sobre la misma fila (falla de inmediato si
  esta tomada). La unica espera real es la del test con dos hilos (0,5 s).
Las lecturas de verificacion se hacen desde una sesion nueva para no ver caches de la ORM.
"""

import threading
import time
from datetime import UTC, date, datetime

import pytest
from app.dominio.conductor import Conductor
from app.dominio.documento import Documento, TipoDocumento
from app.dominio.errores import DniDuplicado
from app.dominio.habilitacion import (
    AccionHabilitacion,
    EstadoHabilitacion,
    EventoHabilitacion,
)
from app.dominio.vehiculo import TipoServicio, TipoVehiculo, Vehiculo
from app.infraestructura.db.modelos import Conductor as ConductorOrm
from app.infraestructura.db.modelos import Vehiculo as VehiculoOrm
from app.infraestructura.repositorios.sql_conductores import SqlRepositorioConductores
from app.infraestructura.repositorios.sql_documentos import SqlRepositorioDocumentos
from app.infraestructura.repositorios.sql_habilitaciones import SqlRepositorioHabilitaciones
from app.infraestructura.repositorios.sql_unidad_de_trabajo import SqlUnidadDeTrabajo
from app.infraestructura.repositorios.sql_vehiculos import SqlRepositorioVehiculos
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError, OperationalError

FECHA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)

# Consulta de la fila con un id, por tipo de entidad bloqueable.
FILA_DE_CONDUCTOR = "SELECT id_conductor FROM conductor WHERE id_conductor = {id}"
FILA_DE_VEHICULO = "SELECT id_vehiculo FROM vehiculo WHERE id_vehiculo = {id}"
BLOQUEABLES = pytest.mark.parametrize(
    ("bloquear", "consulta_de_fila"),
    [
        pytest.param(lambda uow: uow.bloquear_conductor(1), FILA_DE_CONDUCTOR, id="conductor"),
        pytest.param(lambda uow: uow.bloquear_vehiculo(1, 1), FILA_DE_VEHICULO, id="vehiculo"),
    ],
)


class FallaSimulada(Exception):
    """Excepcion propia del test: NotImplementedError es subclase de RuntimeError."""


@pytest.fixture
def uow(fabrica_sesiones, sesion_bd):
    """Depende de `sesion_bd` para que la base se limpie al terminar cada prueba."""
    return SqlUnidadDeTrabajo(fabrica_sesiones)


@pytest.fixture
def datos_sembrados(sesion_bd):
    """Conductores 1 y 2 y vehiculos 1 y 2 del conductor 1, confirmados en la base."""
    for dni in ("30000001", "30000002"):
        sesion_bd.add(
            ConductorOrm(
                dni=dni,
                nombre="Ana",
                apellido="Perez",
                telefono="+54 379 4000000",
                email="ana@example.com",
            )
        )
    sesion_bd.flush()
    for patente in ("AAA111", "BBB222"):
        sesion_bd.add(
            VehiculoOrm(
                id_conductor=1,
                patente=patente,
                marca="Toyota",
                modelo="Etios",
                anio=2019,
                tipo="AUTO",
            )
        )
    sesion_bd.commit()


def nuevo_conductor(dni="30123456"):
    return Conductor.crear(
        dni=dni,
        nombre="Ana",
        apellido="Perez",
        telefono="+54 379 4000000",
        email="ana@example.com",
    )


def nuevo_vehiculo(id_conductor, patente="CCC333"):
    vehiculo = Vehiculo.crear(
        tipo=TipoVehiculo.AUTO,
        patente=patente,
        marca="Toyota",
        modelo="Etios",
        anio=2019,
        tipos_servicio=[TipoServicio.PASAJEROS],
    )
    vehiculo.id_conductor = id_conductor
    return vehiculo


def licencia():
    return Documento.crear(
        tipo=TipoDocumento.LICENCIA,
        numero="LIC-1",
        categoria=None,
        fecha_emision=date(2020, 1, 1),
        fecha_vencimiento=date(2029, 1, 1),
        url_archivo="https://almacen.example.com/lic.pdf",
    )


def evento_de_alta(motivo="Alta del conductor"):
    return EventoHabilitacion(
        accion=AccionHabilitacion.ALTA,
        estado_anterior=None,
        estado_nuevo=EstadoHabilitacion.PENDIENTE,
        motivo=motivo,
        id_operador=None,
        fecha=FECHA,
    )


def contar(fabrica_sesiones, tabla):
    with fabrica_sesiones() as sesion:
        return sesion.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()


def dnis_guardados(fabrica_sesiones):
    with fabrica_sesiones() as sesion:
        return [f[0] for f in sesion.execute(text("SELECT dni FROM conductor ORDER BY dni"))]


# --- Atributos y sesion compartida ---


def test_dentro_del_with_los_atributos_son_los_repositorios_sql(uow):
    with uow as unidad:
        assert unidad is uow
        assert isinstance(uow.conductores, SqlRepositorioConductores)
        assert isinstance(uow.vehiculos, SqlRepositorioVehiculos)
        assert isinstance(uow.documentos, SqlRepositorioDocumentos)
        assert isinstance(uow.habilitaciones, SqlRepositorioHabilitaciones)


def test_los_repositorios_comparten_la_sesion_y_commit_persiste_todo(uow, fabrica_sesiones):
    with uow:
        conductor = uow.conductores.guardar(nuevo_conductor())
        # Sin commit previo: solo funciona si todos usan la misma sesion y transaccion.
        vehiculo = uow.vehiculos.guardar(nuevo_vehiculo(conductor.id))
        uow.documentos.guardar(conductor.id, licencia())
        uow.habilitaciones.registrar_evento_conductor(conductor.id, evento_de_alta())
        uow.habilitaciones.registrar_evento_vehiculo(vehiculo.id, evento_de_alta("Alta vehiculo"))
        uow.commit()

    for tabla in (
        "conductor",
        "vehiculo",
        "documento_conductor",
        "habilitacion_evento_conductor",
        "habilitacion_evento_vehiculo",
    ):
        assert contar(fabrica_sesiones, tabla) == 1, tabla


# --- Transaccion ---


def test_commit_deja_los_datos_visibles_desde_otra_sesion_antes_de_salir_del_with(
    uow, fabrica_sesiones
):
    with uow:
        uow.conductores.guardar(nuevo_conductor("30000001"))
        uow.commit()

        assert dnis_guardados(fabrica_sesiones) == ["30000001"]


def test_salir_del_with_sin_commit_descarta_lo_hecho(uow, fabrica_sesiones):
    with uow:
        uow.conductores.guardar(nuevo_conductor())

    assert dnis_guardados(fabrica_sesiones) == []


def test_salir_del_with_con_una_excepcion_descarta_lo_hecho_y_la_propaga(uow, fabrica_sesiones):
    with pytest.raises(FallaSimulada):
        with uow:
            uow.conductores.guardar(nuevo_conductor())
            raise FallaSimulada("falla a mitad de la transaccion")

    assert dnis_guardados(fabrica_sesiones) == []


def test_rollback_explicito_descarta_lo_pendiente_y_la_uow_sigue_usable(uow, fabrica_sesiones):
    with uow:
        uow.conductores.guardar(nuevo_conductor("30000001"))
        uow.rollback()
        uow.conductores.guardar(nuevo_conductor("30000002"))
        uow.commit()

    assert dnis_guardados(fabrica_sesiones) == ["30000002"]


def test_dos_with_consecutivos_con_el_mismo_objeto_ven_lo_confirmado_y_no_lo_pendiente(uow):
    with uow:
        confirmado = uow.conductores.guardar(nuevo_conductor("30000001"))
        uow.commit()
        pendiente = uow.conductores.guardar(nuevo_conductor("30000002"))

    with uow:
        assert uow.conductores.obtener(confirmado.id) is not None
        assert uow.conductores.obtener(pendiente.id) is None
        assert [c.dni for c in uow.conductores.listar()] == ["30000001"]


def test_un_error_de_dominio_revierte_el_with_y_deja_intacto_lo_confirmado_antes(
    uow, fabrica_sesiones
):
    with uow:
        uow.conductores.guardar(nuevo_conductor("30000001"))
        uow.commit()

    with pytest.raises(DniDuplicado):
        with uow:
            uow.conductores.guardar(nuevo_conductor("30000002"))
            uow.conductores.guardar(nuevo_conductor("30000001"))  # DNI repetido
            uow.commit()

    assert dnis_guardados(fabrica_sesiones) == ["30000001"]


def test_el_conductor_y_su_evento_de_alta_se_guardan_en_la_misma_transaccion(uow, fabrica_sesiones):
    with pytest.raises(IntegrityError):
        with uow:
            conductor = uow.conductores.guardar(nuevo_conductor())
            uow.habilitaciones.registrar_evento_conductor(
                conductor.id,
                evento_de_alta(motivo=""),  # viola ck_..._motivo_requerido
            )
            uow.commit()

    assert contar(fabrica_sesiones, "conductor") == 0
    assert contar(fabrica_sesiones, "habilitacion_evento_conductor") == 0


# --- Bloqueo de fila: valor devuelto ---


def test_bloquear_conductor_devuelve_el_conductor_de_dominio_o_none(uow, datos_sembrados):
    with uow:
        conductor = uow.bloquear_conductor(1)
        inexistente = uow.bloquear_conductor(999)

    assert isinstance(conductor, Conductor)
    assert (conductor.id, conductor.dni) == (1, "30000001")
    assert inexistente is None


def test_bloquear_vehiculo_devuelve_el_vehiculo_de_dominio_solo_si_es_del_conductor(
    uow, datos_sembrados
):
    with uow:
        vehiculo = uow.bloquear_vehiculo(1, 1)
        de_otro_conductor = uow.bloquear_vehiculo(2, 1)
        inexistente = uow.bloquear_vehiculo(1, 999)

    assert isinstance(vehiculo, Vehiculo)
    assert (vehiculo.id, vehiculo.id_conductor, vehiculo.patente) == (1, 1, "AAA111")
    assert de_otro_conductor is None
    assert inexistente is None


@BLOQUEABLES
def test_el_sql_emitido_al_bloquear_contiene_for_update(
    uow, datos_sembrados, engine_integracion, bloquear, consulta_de_fila
):
    sentencias = []

    def registrar(conexion, cursor, sentencia, parametros, contexto, ejecutar_muchos):
        sentencias.append(sentencia.upper())

    event.listen(engine_integracion, "before_cursor_execute", registrar)
    try:
        with uow:
            bloquear(uow)
    finally:
        event.remove(engine_integracion, "before_cursor_execute", registrar)

    assert any("FOR UPDATE" in sentencia for sentencia in sentencias)


# --- Bloqueo de fila: efecto sobre otras sesiones ---


def intentar_bloquear_sin_esperar(fabrica_sesiones, consulta_de_fila, id_fila):
    with fabrica_sesiones() as otra_sesion:
        sql = consulta_de_fila.format(id=id_fila) + " FOR UPDATE NOWAIT"
        return otra_sesion.execute(text(sql)).scalar_one_or_none()


@BLOQUEABLES
def test_mientras_la_uow_tiene_el_bloqueo_otra_sesion_no_puede_tomar_esa_fila(
    uow, datos_sembrados, fabrica_sesiones, bloquear, consulta_de_fila
):
    with uow:
        bloquear(uow)  # sin commit: el bloqueo sigue tomado

        with pytest.raises(OperationalError, match="lock"):
            intentar_bloquear_sin_esperar(fabrica_sesiones, consulta_de_fila, 1)
        # otra fila no esta bloqueada
        assert intentar_bloquear_sin_esperar(fabrica_sesiones, consulta_de_fila, 2) == 2
        # una lectura comun no se bloquea (MVCC)
        with fabrica_sesiones() as lectora:
            assert lectora.execute(text(consulta_de_fila.format(id=1))).scalar_one() == 1


@BLOQUEABLES
def test_el_bloqueo_se_libera_al_confirmar(
    uow, datos_sembrados, fabrica_sesiones, bloquear, consulta_de_fila
):
    with uow:
        bloquear(uow)
        uow.commit()

        assert intentar_bloquear_sin_esperar(fabrica_sesiones, consulta_de_fila, 1) == 1


@BLOQUEABLES
def test_el_bloqueo_se_libera_al_salir_del_with_sin_confirmar(
    uow, datos_sembrados, fabrica_sesiones, bloquear, consulta_de_fila
):
    with uow:
        bloquear(uow)

    assert intentar_bloquear_sin_esperar(fabrica_sesiones, consulta_de_fila, 1) == 1


def test_un_segundo_bloqueo_espera_al_primero_y_despues_lee_lo_que_este_confirmo(
    fabrica_sesiones, datos_sembrados
):
    a_tiene_el_bloqueo = threading.Event()
    soltar_a = threading.Event()
    b_termino = threading.Event()
    estado_visto_por_b = []
    errores = []

    def hilo_a():
        try:
            unidad = SqlUnidadDeTrabajo(fabrica_sesiones)
            with unidad:
                conductor = unidad.bloquear_conductor(1)
                a_tiene_el_bloqueo.set()
                soltar_a.wait(timeout=10)
                conductor.habilitacion = EstadoHabilitacion.APROBADA
                unidad.conductores.guardar(conductor)
                unidad.commit()
        except Exception as error:
            errores.append(error)
            a_tiene_el_bloqueo.set()

    def hilo_b():
        try:
            a_tiene_el_bloqueo.wait(timeout=10)
            unidad = SqlUnidadDeTrabajo(fabrica_sesiones)
            with unidad:
                estado_visto_por_b.append(unidad.bloquear_conductor(1).habilitacion)
            b_termino.set()
        except Exception as error:
            errores.append(error)

    hilos = [threading.Thread(target=hilo_a), threading.Thread(target=hilo_b)]
    for hilo in hilos:
        hilo.start()
    a_tiene_el_bloqueo.wait(timeout=10)
    time.sleep(0.5)
    b_esperaba = not b_termino.is_set()
    soltar_a.set()
    for hilo in hilos:
        hilo.join(timeout=10)

    if errores:
        raise errores[0]
    assert b_esperaba, "B no debio terminar mientras A tenia el bloqueo"
    assert estado_visto_por_b == [EstadoHabilitacion.APROBADA]
