"""Verificacion de los fixtures de integracion (`tests/integracion/conftest.py`).

Comprueba que la base de pruebas responde, esta migrada a head, entrega una `Session`
ligada al engine y aisla las pruebas entre si. El aislamiento no depende del orden de
ejecucion: la misma prueba se corre dos veces y cada corrida exige partir de tablas vacias
y de ids que arrancan en 1, asi que la segunda falla si la primera dejo datos.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.integration

ALEMBIC_INI = Path(__file__).resolve().parents[3] / "infra" / "migraciones" / "alembic.ini"

TABLAS_DE_M3 = (
    "conductor",
    "vehiculo",
    "vehiculo_tipo_servicio",
    "documento_conductor",
    "habilitacion_evento_conductor",
    "habilitacion_evento_vehiculo",
)


def contar_filas(sesion, tabla):
    return sesion.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()


def insertar_conductor(sesion, dni="30123456"):
    return sesion.execute(
        text(
            "INSERT INTO conductor (dni, nombre, apellido, telefono, email) "
            "VALUES (:dni, 'Ana', 'Perez', '+54 379 4000000', 'ana@example.com') "
            "RETURNING id_conductor"
        ),
        {"dni": dni},
    ).scalar_one()


def poblar_todas_las_tablas(sesion):
    """Inserta una fila en cada tabla de M3 y devuelve el id generado de cada una."""
    id_conductor = insertar_conductor(sesion)
    id_vehiculo = sesion.execute(
        text(
            "INSERT INTO vehiculo (id_conductor, patente, marca, modelo, anio, tipo) "
            "VALUES (:id_conductor, 'AB123CD', 'Toyota', 'Etios', 2019, 'AUTO') "
            "RETURNING id_vehiculo"
        ),
        {"id_conductor": id_conductor},
    ).scalar_one()
    id_tipo_servicio = sesion.execute(
        text(
            "INSERT INTO vehiculo_tipo_servicio (id_vehiculo, tipo_servicio) "
            "VALUES (:id_vehiculo, 'PASAJEROS') RETURNING id_vehiculo_tipo_servicio"
        ),
        {"id_vehiculo": id_vehiculo},
    ).scalar_one()
    id_documento = sesion.execute(
        text(
            "INSERT INTO documento_conductor "
            "(id_conductor, numero, fecha_emision, fecha_vencimiento, url_archivo) "
            "VALUES (:id_conductor, 'LIC-1', '2020-01-01', '2029-01-01', "
            "'https://almacen.example.com/lic.pdf') RETURNING id_documento"
        ),
        {"id_conductor": id_conductor},
    ).scalar_one()
    id_evento_conductor = sesion.execute(
        text(
            "INSERT INTO habilitacion_evento_conductor "
            "(id_conductor, estado_nuevo, accion, motivo) "
            "VALUES (:id_conductor, 'PENDIENTE', 'ALTA', 'Alta') RETURNING id_evento"
        ),
        {"id_conductor": id_conductor},
    ).scalar_one()
    id_evento_vehiculo = sesion.execute(
        text(
            "INSERT INTO habilitacion_evento_vehiculo "
            "(id_vehiculo, estado_nuevo, accion, motivo) "
            "VALUES (:id_vehiculo, 'PENDIENTE', 'ALTA', 'Alta') RETURNING id_evento"
        ),
        {"id_vehiculo": id_vehiculo},
    ).scalar_one()
    sesion.commit()
    return {
        "conductor": id_conductor,
        "vehiculo": id_vehiculo,
        "vehiculo_tipo_servicio": id_tipo_servicio,
        "documento_conductor": id_documento,
        "habilitacion_evento_conductor": id_evento_conductor,
        "habilitacion_evento_vehiculo": id_evento_vehiculo,
    }


def test_la_base_responde(sesion_bd):
    assert sesion_bd.execute(text("SELECT 1")).scalar_one() == 1


def test_el_esquema_esta_migrado_con_las_tablas_de_m3(engine_integracion):
    tablas_existentes = set(inspect(engine_integracion).get_table_names())

    assert set(TABLAS_DE_M3) <= tablas_existentes


def test_el_esquema_esta_en_la_revision_head_de_alembic(sesion_bd):
    head = ScriptDirectory.from_config(Config(str(ALEMBIC_INI))).get_current_head()

    revision_aplicada = sesion_bd.execute(
        text("SELECT version_num FROM alembic_version")
    ).scalar_one()

    assert revision_aplicada == head


def test_la_url_expuesta_permite_abrir_una_conexion_independiente(url_integracion):
    motor = create_engine(url_integracion)
    try:
        with motor.connect() as conexion:
            assert conexion.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        motor.dispose()


def test_la_sesion_esta_ligada_al_engine_expuesto(sesion_bd, engine_integracion):
    assert sesion_bd.get_bind() is engine_integracion
    assert sesion_bd.expire_on_commit is False


@pytest.mark.parametrize("corrida", ["primera", "segunda"])
def test_cada_prueba_parte_de_tablas_vacias_y_ids_en_uno(sesion_bd, corrida):
    for tabla in TABLAS_DE_M3:
        assert contar_filas(sesion_bd, tabla) == 0, tabla

    ids = poblar_todas_las_tablas(sesion_bd)

    assert ids == dict.fromkeys(TABLAS_DE_M3, 1)


@pytest.mark.parametrize("corrida", ["primera", "segunda"])
def test_la_limpieza_funciona_aunque_la_prueba_deje_la_transaccion_en_error(sesion_bd, corrida):
    for tabla in TABLAS_DE_M3:
        assert contar_filas(sesion_bd, tabla) == 0, tabla
    assert insertar_conductor(sesion_bd) == 1
    sesion_bd.commit()

    with pytest.raises(IntegrityError):
        insertar_conductor(sesion_bd)  # mismo DNI: viola la unicidad

    # No se hace rollback a proposito: el fixture debe hacerlo antes de limpiar.


def test_dos_sesiones_distintas_ven_los_datos_confirmados(sesion_bd, fabrica_sesiones):
    with fabrica_sesiones() as otra_sesion:
        id_conductor = insertar_conductor(sesion_bd)
        assert contar_filas(otra_sesion, "conductor") == 0  # aun sin confirmar

        sesion_bd.commit()

        otra_sesion.rollback()  # cierra la transaccion de la lectura anterior
        assert contar_filas(otra_sesion, "conductor") == 1
        assert otra_sesion.execute(text("SELECT id_conductor FROM conductor")).scalar_one() == (
            id_conductor
        )
        assert otra_sesion is not sesion_bd
