"""T080: esquema, unicidad, CHECK, claves foráneas y defaults de M3."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.infraestructura.db.modelos import Base
from sqlalchemy import CheckConstraint, UniqueConstraint, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

TABLAS = {
    "conductor",
    "vehiculo",
    "vehiculo_tipo_servicio",
    "documento_conductor",
    "habilitacion_evento_conductor",
    "habilitacion_evento_vehiculo",
}


def _checks(tabla: str) -> str:
    return " ".join(
        str(constraint.sqltext)
        for constraint in Base.metadata.tables[tabla].constraints
        if isinstance(constraint, CheckConstraint)
    )


def test_existen_las_seis_tablas_en_el_metadata() -> None:
    assert TABLAS <= set(Base.metadata.tables)


def test_conductor_dni_y_vehiculo_patente_son_unicos_en_el_metadata() -> None:
    uniques_conductor = {
        constraint.name
        for constraint in Base.metadata.tables["conductor"].constraints
        if isinstance(constraint, UniqueConstraint)
    }
    uniques_vehiculo = {
        constraint.name
        for constraint in Base.metadata.tables["vehiculo"].constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert "uq_conductor_dni" in uniques_conductor
    assert "uq_vehiculo_patente" in uniques_vehiculo


def test_checks_de_estados_tipos_y_acciones_en_el_metadata() -> None:
    checks_conductor = _checks("conductor")
    checks_vehiculo = _checks("vehiculo")
    checks_servicio = _checks("vehiculo_tipo_servicio")
    checks_evento_conductor = _checks("habilitacion_evento_conductor")
    checks_evento_vehiculo = _checks("habilitacion_evento_vehiculo")

    for estado in ("PENDIENTE", "OBSERVADA", "APROBADA", "SUSPENDIDA", "RECHAZADA"):
        assert estado in checks_conductor
        assert estado in checks_vehiculo
        assert estado in checks_evento_conductor
        assert estado in checks_evento_vehiculo

    assert "'AUTO'" in checks_vehiculo
    assert "'MOTO'" in checks_vehiculo
    assert "'PASAJEROS'" in checks_servicio
    assert "'ENVIOS'" in checks_servicio

    for accion in ("ALTA", "APROBAR", "OBSERVAR", "SUSPENDER", "RECHAZAR"):
        assert accion in checks_evento_conductor
        assert accion in checks_evento_vehiculo


def test_defaults_de_habilitacion_y_estado_operativo_en_el_metadata() -> None:
    conductor = Base.metadata.tables["conductor"]
    vehiculo = Base.metadata.tables["vehiculo"]
    tipo_servicio = Base.metadata.tables["vehiculo_tipo_servicio"]

    assert "PENDIENTE" in str(conductor.c.estado_habilitacion.server_default.arg)
    assert "PENDIENTE" in str(vehiculo.c.estado_habilitacion.server_default.arg)
    assert str(conductor.c.conectado.server_default.arg).lower() == "false"
    assert str(conductor.c.disponible.server_default.arg).lower() == "false"
    assert str(tipo_servicio.c.habilitado.server_default.arg).lower() == "false"


def test_claves_foraneas_en_el_metadata() -> None:
    esperadas = {
        ("vehiculo", "id_conductor", "conductor", "id_conductor"),
        (
            "vehiculo_tipo_servicio",
            "id_vehiculo",
            "vehiculo",
            "id_vehiculo",
        ),
        (
            "documento_conductor",
            "id_conductor",
            "conductor",
            "id_conductor",
        ),
        (
            "habilitacion_evento_conductor",
            "id_conductor",
            "conductor",
            "id_conductor",
        ),
        (
            "habilitacion_evento_vehiculo",
            "id_vehiculo",
            "vehiculo",
            "id_vehiculo",
        ),
    }
    encontradas = set()
    for tabla in Base.metadata.tables.values():
        for fk in tabla.foreign_keys:
            encontradas.add((tabla.name, fk.parent.name, fk.column.table.name, fk.column.name))

    assert esperadas <= encontradas


@pytest.fixture
def motor(m3_migrada: str) -> Iterator[Engine]:
    engine = create_engine(m3_migrada)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.mark.integration
def test_postgres_contiene_todas_las_tablas(m3_migrada: str) -> None:
    from sqlalchemy import inspect

    engine = create_engine(m3_migrada)
    try:
        tablas = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert TABLAS <= tablas
    assert "alembic_version" in tablas


@pytest.mark.integration
def test_postgres_tiene_unicidad_y_checks(m3_migrada: str) -> None:
    engine = create_engine(m3_migrada)
    try:
        with engine.connect() as conexion:
            uniques = {
                fila[0]
                for fila in conexion.execute(
                    text(
                        """
                        SELECT conname
                        FROM pg_constraint
                        WHERE conrelid IN ('conductor'::regclass, 'vehiculo'::regclass)
                          AND contype = 'u'
                        """
                    )
                )
            }
            checks = {
                fila[0]: fila[1]
                for fila in conexion.execute(
                    text(
                        """
                        SELECT conname, pg_get_constraintdef(oid)
                        FROM pg_constraint
                        WHERE conrelid IN (
                            'conductor'::regclass,
                            'vehiculo'::regclass,
                            'vehiculo_tipo_servicio'::regclass,
                            'habilitacion_evento_conductor'::regclass,
                            'habilitacion_evento_vehiculo'::regclass
                        )
                          AND contype = 'c'
                        """
                    )
                )
            }
    finally:
        engine.dispose()

    assert {"uq_conductor_dni", "uq_vehiculo_patente"} <= uniques
    for clave in (
        "ck_conductor_estado_habilitacion",
        "ck_vehiculo_tipo",
        "ck_vehiculo_estado_habilitacion",
        "ck_vehiculo_tipo_servicio_tipo_servicio",
        "ck_habilitacion_evento_conductor_accion",
        "ck_habilitacion_evento_vehiculo_accion",
    ):
        assert clave in checks
    definiciones = " ".join(checks.values())
    for valor in (
        "PENDIENTE",
        "OBSERVADA",
        "APROBADA",
        "SUSPENDIDA",
        "RECHAZADA",
        "AUTO",
        "MOTO",
        "PASAJEROS",
        "ENVIOS",
        "ALTA",
        "APROBAR",
        "OBSERVAR",
        "SUSPENDER",
        "RECHAZAR",
    ):
        assert valor in definiciones


@pytest.mark.integration
def test_defaults_reales_pendiente_falso_y_falso(motor: Engine) -> None:
    with motor.begin() as conexion:
        conexion.execute(
            text(
                """
                INSERT INTO conductor (dni, nombre, apellido, telefono, email)
                VALUES ('20000001', 'Default', 'Prueba', '3624000099', 'default@m3.local')
                """
            )
        )
        estado, conectado, disponible = conexion.execute(
            text(
                """
                SELECT estado_habilitacion, conectado, disponible
                FROM conductor WHERE dni = '20000001'
                """
            )
        ).one()

    assert (estado, conectado, disponible) == ("PENDIENTE", False, False)


@pytest.mark.integration
def test_la_base_rechaza_dni_duplicado(motor: Engine) -> None:
    with motor.begin() as conexion:
        conexion.execute(
            text(
                """
                INSERT INTO conductor (dni, nombre, apellido, telefono, email)
                VALUES ('20000002', 'Uno', 'Prueba', '3624000098', 'uno@m3.local')
                """
            )
        )

    with pytest.raises(IntegrityError):
        with motor.begin() as conexion:
            conexion.execute(
                text(
                    """
                    INSERT INTO conductor (dni, nombre, apellido, telefono, email)
                    VALUES ('20000002', 'Dos', 'Prueba', '3624000097', 'dos@m3.local')
                    """
                )
            )


@pytest.mark.integration
def test_la_base_rechaza_estado_de_habilitacion_invalido(motor: Engine) -> None:
    with pytest.raises(IntegrityError):
        with motor.begin() as conexion:
            conexion.execute(
                text(
                    """
                    INSERT INTO conductor
                        (dni, nombre, apellido, telefono, email, estado_habilitacion)
                    VALUES
                        ('20000003', 'Estado', 'Invalido', '3624000096',
                         'estado@m3.local', 'EN_REVISION')
                    """
                )
            )


@pytest.mark.integration
def test_la_base_rechaza_tipo_de_vehiculo_invalido(motor: Engine) -> None:
    with motor.begin() as conexion:
        id_conductor = conexion.execute(
            text(
                """
                INSERT INTO conductor (dni, nombre, apellido, telefono, email)
                VALUES ('20000004', 'Tipo', 'Invalido', '3624000095', 'tipo@m3.local')
                RETURNING id_conductor
                """
            )
        ).scalar_one()

    with pytest.raises(IntegrityError):
        with motor.begin() as conexion:
            conexion.execute(
                text(
                    """
                    INSERT INTO vehiculo
                        (id_conductor, patente, marca, modelo, anio, tipo)
                    VALUES
                        (:id_conductor, 'ZZ999ZZ', 'Marca', 'Modelo', 2020, 'CAMION')
                    """
                ),
                {"id_conductor": id_conductor},
            )
