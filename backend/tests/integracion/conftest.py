"""Fixtures de integracion para los repositorios SQL (T097).

Contrato (lo fija `test_conftest.py`):
- `url_integracion` (scope session): URL SQLAlchemy de una base PostgreSQL de un contenedor
  efimero (imagen `postgres:17.11-alpine`), con el esquema migrado a head.
- `engine_integracion` (scope session): engine ligado a esa URL.
- `fabrica_sesiones` (scope session): `sessionmaker` creado con `crear_sessionmaker`, para
  abrir sesiones adicionales (por ejemplo, en pruebas de concurrencia).
- `sesion_bd` (scope function): `Session` ligada al engine; al terminar cada prueba se
  vacian todas las tablas de M3 con `TRUNCATE ... RESTART IDENTITY CASCADE`.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.infraestructura.db.sesion import crear_engine, crear_sessionmaker
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.community.postgres import PostgresContainer

RAIZ_DEL_REPOSITORIO = Path(__file__).resolve().parents[3]
ALEMBIC_INI = RAIZ_DEL_REPOSITORIO / "infra" / "migraciones" / "alembic.ini"
DIRECTORIO_DE_INTEGRACION = Path(__file__).resolve().parent

IMAGEN_POSTGRES = "postgres:17.11-alpine"
USUARIO_DE_PRUEBA = "m3_test"
CLAVE_DE_PRUEBA = "test-clave-no-real"
BASE_DE_PRUEBA = "m3_test"

TABLAS_DE_M3 = (
    "conductor",
    "vehiculo",
    "vehiculo_tipo_servicio",
    "documento_conductor",
    "habilitacion_evento_conductor",
    "habilitacion_evento_vehiculo",
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Marca como `integration` todos los tests de este directorio."""
    for item in items:
        if DIRECTORIO_DE_INTEGRACION in item.path.parents:
            item.add_marker(pytest.mark.integration)


def _docker_disponible() -> bool:
    try:
        import docker

        return bool(docker.from_env(timeout=2).ping())
    except Exception:
        return False


def _migrar_a_head(url: str) -> None:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")


@pytest.fixture(scope="session")
def url_integracion() -> Iterator[str]:
    if not _docker_disponible():
        pytest.skip("Docker no esta disponible: se omiten las pruebas de integracion.")
    contenedor = PostgresContainer(
        IMAGEN_POSTGRES,
        username=USUARIO_DE_PRUEBA,
        password=CLAVE_DE_PRUEBA,
        dbname=BASE_DE_PRUEBA,
        driver="psycopg",
    )
    with contenedor:
        url = contenedor.get_connection_url()
        _migrar_a_head(url)
        yield url


@pytest.fixture(scope="session")
def engine_integracion(url_integracion: str) -> Iterator[Engine]:
    engine = crear_engine(url_integracion)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def fabrica_sesiones(engine_integracion: Engine) -> sessionmaker[Session]:
    return crear_sessionmaker(engine_integracion)


@pytest.fixture
def sesion_bd(
    engine_integracion: Engine, fabrica_sesiones: sessionmaker[Session]
) -> Iterator[Session]:
    sesion = fabrica_sesiones()
    try:
        yield sesion
    finally:
        sesion.rollback()
        sesion.close()
        with engine_integracion.begin() as conexion:
            conexion.execute(text(f"TRUNCATE {', '.join(TABLAS_DE_M3)} RESTART IDENTITY CASCADE"))
