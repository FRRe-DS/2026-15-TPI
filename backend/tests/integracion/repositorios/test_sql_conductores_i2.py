"""Campos de la Iteracion 2 del conductor sobre PostgreSQL (T347).

La migracion `0002` agrega `estado` con `CHECK`, el vehiculo activo con `FK`,
la fecha del ultimo cambio de estado, los totales de puntajes y la ubicacion.
Estos tests usan el repositorio SQL real y confirman la transaccion para leer
desde otra sesion, de modo que lo que se comprueba es la fila, no el objeto en
memoria.
"""

from datetime import UTC, datetime

import pytest
from app.dominio.conductor import Conductor, EstadoConductor
from app.dominio.habilitacion import EstadoHabilitacion
from app.infraestructura.db.modelos import Vehiculo as VehiculoOrm
from app.infraestructura.repositorios.sql_conductores import SqlRepositorioConductores
from app.infraestructura.repositorios.sql_unidad_de_trabajo import SqlUnidadDeTrabajo
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
DISPONIBLE = EstadoConductor.DISPONIBLE


@pytest.fixture
def repositorio(sesion_bd):
    return SqlRepositorioConductores(sesion_bd)


def nuevo_conductor(dni="30123456", **campos):
    conductor = Conductor.crear(
        dni=dni,
        nombre="Ana",
        apellido="Perez",
        telefono="+54 379 4000000",
        email="ana@example.com",
    )
    conductor.habilitacion = EstadoHabilitacion.APROBADA
    for atributo, valor in campos.items():
        setattr(conductor, atributo, valor)
    return conductor


def sembrar_vehiculo(sesion, id_conductor, patente="AAA111"):
    vehiculo = VehiculoOrm(
        id_conductor=id_conductor,
        patente=patente,
        marca="Toyota",
        modelo="Etios",
        anio=2019,
        tipo="AUTO",
    )
    sesion.add(vehiculo)
    sesion.flush()
    return vehiculo.id_vehiculo


def leer_despues_de_confirmar(sesion_bd, fabrica_sesiones, id_conductor):
    sesion_bd.commit()
    with fabrica_sesiones() as otra_sesion:
        return SqlRepositorioConductores(otra_sesion).obtener(id_conductor)


# --- estado ---


@pytest.mark.parametrize("estado", list(EstadoConductor))
def test_guardar_y_obtener_persisten_los_cuatro_estados(
    repositorio, sesion_bd, fabrica_sesiones, estado
):
    guardado = repositorio.guardar(nuevo_conductor(estado=estado))

    leido = leer_despues_de_confirmar(sesion_bd, fabrica_sesiones, guardado.id)

    assert leido.estado is estado


def test_la_base_rechaza_un_estado_fuera_del_enum(repositorio, sesion_bd):
    guardado = repositorio.guardar(nuevo_conductor())
    sesion_bd.commit()

    with pytest.raises(IntegrityError):
        sesion_bd.execute(
            text("UPDATE conductor SET estado = 'VOLANDO' WHERE id_conductor = :id"),
            {"id": guardado.id},
        )
    sesion_bd.rollback()


# --- campos nuevos: valores por defecto ---


def test_los_campos_nuevos_arrancan_vacios_y_en_cero(repositorio, sesion_bd, fabrica_sesiones):
    guardado = repositorio.guardar(nuevo_conductor())

    leido = leer_despues_de_confirmar(sesion_bd, fabrica_sesiones, guardado.id)

    assert leido.id_vehiculo_activo is None
    assert leido.fecha_ultimo_cambio_estado is None
    assert leido.suma_puntajes == 0
    assert leido.cantidad_calificaciones == 0


# --- vehiculo activo ---


def test_id_vehiculo_activo_se_persiste_y_apunta_a_un_vehiculo(
    repositorio, sesion_bd, fabrica_sesiones
):
    conductor = repositorio.guardar(nuevo_conductor())
    id_vehiculo = sembrar_vehiculo(sesion_bd, conductor.id)
    conductor.id_vehiculo_activo = id_vehiculo
    repositorio.guardar(conductor)

    leido = leer_despues_de_confirmar(sesion_bd, fabrica_sesiones, conductor.id)

    assert leido.id_vehiculo_activo == id_vehiculo


def test_la_base_rechaza_un_vehiculo_activo_que_no_existe(repositorio):
    conductor = repositorio.guardar(nuevo_conductor())
    conductor.id_vehiculo_activo = 999

    with pytest.raises(IntegrityError):
        repositorio.guardar(conductor)


# --- fecha del ultimo cambio de estado ---


def test_fecha_ultimo_cambio_estado_se_persiste_con_zona_horaria(
    repositorio, sesion_bd, fabrica_sesiones
):
    conductor = repositorio.guardar(nuevo_conductor(estado=DISPONIBLE))
    conductor.fecha_ultimo_cambio_estado = AHORA
    repositorio.guardar(conductor)

    leido = leer_despues_de_confirmar(sesion_bd, fabrica_sesiones, conductor.id)

    assert leido.fecha_ultimo_cambio_estado == AHORA
    assert leido.fecha_ultimo_cambio_estado.utcoffset() is not None


# --- puntajes ---


def test_los_totales_de_puntajes_se_persisten(repositorio, sesion_bd, fabrica_sesiones):
    conductor = repositorio.guardar(nuevo_conductor())
    conductor.suma_puntajes = 18
    conductor.cantidad_calificaciones = 5
    repositorio.guardar(conductor)

    leido = leer_despues_de_confirmar(sesion_bd, fabrica_sesiones, conductor.id)

    assert leido.suma_puntajes == 18
    assert leido.cantidad_calificaciones == 5


@pytest.mark.parametrize(
    ("suma_puntajes", "cantidad_calificaciones"),
    [(-1, 0), (0, -1)],
    ids=["suma-negativa", "cantidad-negativa"],
)
def test_la_base_rechaza_puntajes_negativos(repositorio, suma_puntajes, cantidad_calificaciones):
    conductor = repositorio.guardar(nuevo_conductor())
    conductor.suma_puntajes = suma_puntajes
    conductor.cantidad_calificaciones = cantidad_calificaciones

    with pytest.raises(IntegrityError):
        repositorio.guardar(conductor)


# --- ubicacion ---


def test_guardar_persiste_la_ubicacion_del_conductor(repositorio, sesion_bd, fabrica_sesiones):
    conductor = repositorio.guardar(nuevo_conductor())
    conductor.fijar_ubicacion(-27.4511, -58.9867, AHORA)
    repositorio.guardar(conductor)

    leido = leer_despues_de_confirmar(sesion_bd, fabrica_sesiones, conductor.id)

    assert (leido.latitud, leido.longitud) == (-27.4511, -58.9867)
    assert leido.fecha_act_ubic == AHORA


# --- unidad de trabajo: bloqueo ---


def test_bloquear_conductor_devuelve_los_campos_nuevos(repositorio, sesion_bd, fabrica_sesiones):
    conductor = repositorio.guardar(nuevo_conductor(estado=DISPONIBLE))
    id_vehiculo = sembrar_vehiculo(sesion_bd, conductor.id)
    conductor.id_vehiculo_activo = id_vehiculo
    conductor.fecha_ultimo_cambio_estado = AHORA
    conductor.suma_puntajes = 9
    conductor.cantidad_calificaciones = 3
    repositorio.guardar(conductor)
    sesion_bd.commit()

    with SqlUnidadDeTrabajo(fabrica_sesiones) as uow:
        bloqueado = uow.bloquear_conductor(conductor.id)

    assert bloqueado is not None
    assert bloqueado.estado is DISPONIBLE
    assert bloqueado.id_vehiculo_activo == id_vehiculo
    assert bloqueado.fecha_ultimo_cambio_estado == AHORA
    assert bloqueado.suma_puntajes == 9
    assert bloqueado.cantidad_calificaciones == 3


def test_bloquear_un_conductor_inexistente_devuelve_none(sesion_bd, fabrica_sesiones):
    with SqlUnidadDeTrabajo(fabrica_sesiones) as uow:
        assert uow.bloquear_conductor(999) is None
