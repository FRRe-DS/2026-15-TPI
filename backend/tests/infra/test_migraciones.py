"""T082: Alembic upgrade head crea el esquema y downgrade base lo elimina."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.infraestructura.db.modelos import Base
from sqlalchemy import create_engine, inspect, text

RAIZ = Path(__file__).resolve().parents[3]
ALEMBIC_INI = RAIZ / "infra" / "migraciones" / "alembic.ini"
ENV_PY = RAIZ / "infra" / "migraciones" / "env.py"
VERSION = RAIZ / "infra" / "migraciones" / "versions" / "0001_esquema_inicial.py"
TABLAS = set(Base.metadata.tables)


def test_existen_los_archivos_de_migracion() -> None:
    assert ALEMBIC_INI.is_file()
    assert ENV_PY.is_file()
    assert VERSION.is_file()


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
        assert version == "0001"
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
