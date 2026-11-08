"""Migraciones de M3: esquema completo, revisión 0002 y reversibilidad."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.infraestructura.db.modelos import Base
from sqlalchemy import create_engine, inspect, text

RAIZ = Path(__file__).resolve().parents[3]
ALEMBIC_INI = RAIZ / "infra" / "migraciones" / "alembic.ini"
ENV_PY = RAIZ / "infra" / "migraciones" / "env.py"
VERSION_1 = RAIZ / "infra" / "migraciones" / "versions" / "0001_esquema_inicial.py"
VERSION_2 = RAIZ / "infra" / "migraciones" / "versions" / "0002_iteracion2.py"
TABLAS = set(Base.metadata.tables)


def test_existen_los_archivos_de_migracion() -> None:
    assert ALEMBIC_INI.is_file()
    assert ENV_PY.is_file()
    assert VERSION_1.is_file()
    assert VERSION_2.is_file()


def test_alembic_ini_no_versiona_credenciales() -> None:
    contenido = ALEMBIC_INI.read_text(encoding="utf-8")
    linea_url = next(
        linea for linea in contenido.splitlines() if linea.strip().startswith("sqlalchemy.url")
    )
    assert linea_url.split("=", 1)[1].strip() == ""


def test_env_py_resuelve_la_url_desde_el_entorno() -> None:
    contenido = ENV_PY.read_text(encoding="utf-8")
    assert "DATABASE_URL" in contenido
    assert "postgresql+psycopg://" not in contenido


@pytest.mark.integration
def test_upgrade_head_crea_el_esquema(base_temporal: str, migrar: object) -> None:
    migrar(base_temporal, "head")  # type: ignore[operator]
    engine = create_engine(base_temporal)
    try:
        inspector = inspect(engine)
        tablas = set(inspector.get_table_names())
        assert TABLAS <= tablas
        assert "alembic_version" in tablas
        with engine.connect() as conexion:
            version = conexion.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert version == "0002"
    finally:
        engine.dispose()


@pytest.mark.integration
def test_downgrade_base_elimina_el_esquema(
    base_temporal: str, migrar: object, revertir: object
) -> None:
    migrar(base_temporal, "head")  # type: ignore[operator]
    revertir(base_temporal, "base")  # type: ignore[operator]

    engine = create_engine(base_temporal)
    try:
        tablas = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert TABLAS.isdisjoint(tablas)


@pytest.mark.integration
def test_se_puede_volver_a_migrar_despues_del_downgrade(
    base_temporal: str, migrar: object, revertir: object
) -> None:
    migrar(base_temporal, "head")  # type: ignore[operator]
    revertir(base_temporal, "base")  # type: ignore[operator]
    migrar(base_temporal, "head")  # type: ignore[operator]

    engine = create_engine(base_temporal)
    try:
        tablas = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert TABLAS <= tablas


@pytest.mark.integration
def test_0002_migra_los_booleanos_existentes_a_estado(base_temporal: str, migrar: object) -> None:
    migrar(base_temporal, "0001")  # type: ignore[operator]
    engine = create_engine(base_temporal)
    try:
        with engine.begin() as conexion:
            conexion.execute(
                text(
                    """
                    INSERT INTO conductor
                        (dni, nombre, apellido, telefono, email, conectado, disponible)
                    VALUES
                        ('20000001', 'Des', 'Conectado', '3624000001',
                         'desconectado@m3.local', false, false),
                        ('20000002', 'Dis', 'Ponible', '3624000002',
                         'disponible@m3.local', true, true),
                        ('20000003', 'Con', 'Conectado', '3624000003',
                         'conectado@m3.local', true, false)
                    """
                )
            )
    finally:
        engine.dispose()

    migrar(base_temporal, "head")  # type: ignore[operator]

    engine = create_engine(base_temporal)
    try:
        with engine.connect() as conexion:
            estados = dict(conexion.execute(text("SELECT dni, estado FROM conductor")).all())
        columnas = {columna["name"] for columna in inspect(engine).get_columns("conductor")}
    finally:
        engine.dispose()

    assert estados == {
        "20000001": "DESCONECTADO",
        "20000002": "DISPONIBLE",
        "20000003": "CONECTADO",
    }
    assert "conectado" not in columnas
    assert "disponible" not in columnas


@pytest.mark.integration
def test_0002_downgrade_reconstruye_los_booleanos(
    base_temporal: str, migrar: object, revertir: object
) -> None:
    migrar(base_temporal, "head")  # type: ignore[operator]
    engine = create_engine(base_temporal)
    try:
        with engine.begin() as conexion:
            conexion.execute(
                text(
                    """
                    INSERT INTO conductor
                        (dni, nombre, apellido, telefono, email, estado)
                    VALUES
                        ('20000011', 'Des', 'Conectado', '3624000011',
                         'd1@m3.local', 'DESCONECTADO'),
                        ('20000012', 'Dis', 'Ponible', '3624000012',
                         'd2@m3.local', 'DISPONIBLE'),
                        ('20000013', 'Con', 'Conectado', '3624000013',
                         'd3@m3.local', 'CONECTADO'),
                        ('20000014', 'Ocu', 'Pado', '3624000014',
                         'd4@m3.local', 'OCUPADO')
                    """
                )
            )
    finally:
        engine.dispose()

    revertir(base_temporal, "0001")  # type: ignore[operator]

    engine = create_engine(base_temporal)
    try:
        with engine.connect() as conexion:
            filas = {
                dni: (conectado, disponible)
                for dni, conectado, disponible in conexion.execute(
                    text("SELECT dni, conectado, disponible FROM conductor")
                )
            }
        columnas = {columna["name"] for columna in inspect(engine).get_columns("conductor")}
    finally:
        engine.dispose()

    assert filas == {
        "20000011": (False, False),
        "20000012": (True, True),
        "20000013": (True, False),
        "20000014": (True, False),
    }
    assert "estado" not in columnas


@pytest.mark.integration
def test_0002_sincroniza_habilitado_con_la_habilitacion_del_vehiculo(
    base_temporal: str, migrar: object
) -> None:
    migrar(base_temporal, "0001")  # type: ignore[operator]
    engine = create_engine(base_temporal)
    try:
        with engine.begin() as conexion:
            id_conductor = conexion.execute(
                text(
                    """
                    INSERT INTO conductor (dni, nombre, apellido, telefono, email)
                    VALUES ('20000021', 'Ana', 'Perez', '3624000021', 'ana@m3.local')
                    RETURNING id_conductor
                    """
                )
            ).scalar_one()
            id_vehiculo = conexion.execute(
                text(
                    """
                    INSERT INTO vehiculo
                        (id_conductor, patente, marca, modelo, anio, tipo, estado_habilitacion)
                    VALUES
                        (:id_conductor, 'AB123CD', 'Toyota', 'Corolla', 2022, 'AUTO', 'APROBADA')
                    RETURNING id_vehiculo
                    """
                ),
                {"id_conductor": id_conductor},
            ).scalar_one()
            conexion.execute(
                text(
                    """
                    INSERT INTO vehiculo_tipo_servicio (id_vehiculo, tipo_servicio, habilitado)
                    VALUES (:id_vehiculo, 'PASAJEROS', false)
                    """
                ),
                {"id_vehiculo": id_vehiculo},
            )
    finally:
        engine.dispose()

    migrar(base_temporal, "head")  # type: ignore[operator]

    engine = create_engine(base_temporal)
    try:
        with engine.connect() as conexion:
            habilitado = conexion.execute(
                text("SELECT habilitado FROM vehiculo_tipo_servicio")
            ).scalar_one()
    finally:
        engine.dispose()

    assert habilitado is True
