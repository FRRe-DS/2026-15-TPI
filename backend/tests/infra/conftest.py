"""Fixtures de integración para el esquema, las migraciones y el seed.

Los tests que necesitan Docker se marcan como ``integration`` y se omiten con
un mensaje claro si el daemon no está disponible. Las pruebas estáticas del
esquema y del realm corren siempre.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy import URL

RAIZ = Path(__file__).resolve().parents[3]
ALEMBIC_INI = RAIZ / "infra" / "migraciones" / "alembic.ini"
INIT_SCRIPT = RAIZ / "infra" / "postgres" / "init" / "01-crear-bases.sh"

POSTGRES_IMAGE = "postgres:17.11-alpine"
SUPERUSER = "postgres"
SUPERPASSWORD = "test-superuser-no-real"
M3_USUARIO = "m3"
M3_CLAVE = "test-m3-no-real"
M3_BASE = "m3"
KC_USUARIO = "keycloak"
KC_CLAVE = "test-keycloak-no-real"
KC_BASE = "keycloak"


def _docker_disponible() -> bool:
    try:
        import docker

        cliente = docker.from_env(timeout=2)
        return bool(cliente.ping())
    except Exception:
        return False


DOCKER_DISPONIBLE = _docker_disponible()


@pytest.fixture(scope="session")
def requiere_docker() -> None:
    if not DOCKER_DISPONIBLE:
        pytest.skip("Docker no está disponible: se omite la prueba de integración.")


def _conectar_admin(contenedor: Any, base: str = "postgres") -> psycopg.Connection:
    return psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=int(contenedor.get_exposed_port(5432)),
        user=SUPERUSER,
        password=SUPERPASSWORD,
        dbname=base,
        connect_timeout=3,
        autocommit=True,
    )


def _esperar_postgres(contenedor: Any) -> None:
    ultimo_error: Exception | None = None
    for _ in range(60):
        try:
            with _conectar_admin(contenedor):
                return
        except Exception as error:  # pragma: no cover - depende del arranque real
            ultimo_error = error
            time.sleep(1)
    raise RuntimeError(f"PostgreSQL no respondió a tiempo: {ultimo_error}")


def _bases_creadas(contenedor: Any) -> bool:
    with _conectar_admin(contenedor) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT datname FROM pg_database WHERE datname = ANY(%s)",
                ([M3_BASE, KC_BASE],),
            )
            return {fila[0] for fila in cursor.fetchall()} == {M3_BASE, KC_BASE}


@pytest.fixture(scope="session")
def postgres(requiere_docker: None) -> Iterator[Any]:
    """Contenedor PostgreSQL con el script de inicialización montado."""

    from testcontainers.postgres import PostgresContainer

    contenedor = PostgresContainer(
        POSTGRES_IMAGE,
        username=SUPERUSER,
        password=SUPERPASSWORD,
        dbname="postgres",
        driver="psycopg",
    )
    for clave, valor in {
        "M3_DB_NAME": M3_BASE,
        "M3_DB_USER": M3_USUARIO,
        "M3_DB_PASSWORD": M3_CLAVE,
        "KEYCLOAK_DB_NAME": KC_BASE,
        "KEYCLOAK_DB_USER": KC_USUARIO,
        "KEYCLOAK_DB_PASSWORD": KC_CLAVE,
    }.items():
        contenedor.with_env(clave, valor)
    contenedor.with_volume_mapping(
        str(INIT_SCRIPT), "/docker-entrypoint-initdb.d/01-crear-bases.sh", "ro"
    )
    contenedor.start()
    try:
        _esperar_postgres(contenedor)
        if not _bases_creadas(contenedor):
            # En Windows el bit ejecutable del bind mount puede perderse.
            codigo, salida = contenedor.exec(
                ["bash", "/docker-entrypoint-initdb.d/01-crear-bases.sh"]
            )
            if codigo != 0:
                raise RuntimeError("Falló 01-crear-bases.sh: " + salida.decode(errors="replace"))
            for _ in range(30):
                if _bases_creadas(contenedor):
                    break
                time.sleep(1)
            else:
                raise RuntimeError("El script no creó las bases esperadas.")
        yield contenedor
    finally:
        contenedor.stop()


def url_sqlalchemy(contenedor: Any, base: str, usuario: str, clave: str) -> str:
    return URL.create(
        "postgresql+psycopg",
        username=usuario,
        password=clave,
        host=contenedor.get_container_host_ip(),
        port=int(contenedor.get_exposed_port(5432)),
        database=base,
    ).render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def url_m3(postgres: Any) -> str:
    return url_sqlalchemy(postgres, M3_BASE, M3_USUARIO, M3_CLAVE)


@pytest.fixture(scope="session")
def datos_conexion(postgres: Any) -> dict[str, Any]:
    return {
        "host": postgres.get_container_host_ip(),
        "port": int(postgres.get_exposed_port(5432)),
        "superusuario": SUPERUSER,
        "superclave": SUPERPASSWORD,
        "m3_usuario": M3_USUARIO,
        "m3_clave": M3_CLAVE,
        "m3_base": M3_BASE,
        "keycloak_usuario": KC_USUARIO,
        "keycloak_clave": KC_CLAVE,
        "keycloak_base": KC_BASE,
    }


def aplicar_migraciones(url: str, revision: str = "head") -> None:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, revision)


def revertir_migraciones(url: str, revision: str = "base") -> None:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", url)
    command.downgrade(config, revision)


@pytest.fixture(scope="session")
def migrar() -> Any:
    return aplicar_migraciones


@pytest.fixture(scope="session")
def revertir() -> Any:
    return revertir_migraciones


@pytest.fixture(scope="session")
def m3_migrada(postgres: Any, url_m3: str) -> str:
    aplicar_migraciones(url_m3)
    return url_m3


@pytest.fixture
def base_temporal(postgres: Any) -> Iterator[str]:
    """Crea una base descartable propiedad del usuario m3."""

    nombre = f"m3_test_{uuid.uuid4().hex[:12]}"
    with _conectar_admin(postgres) as conexion:
        conexion.execute(
            sql.SQL("CREATE DATABASE {} OWNER {}").format(
                sql.Identifier(nombre), sql.Identifier(M3_USUARIO)
            )
        )
    try:
        yield url_sqlalchemy(postgres, nombre, M3_USUARIO, M3_CLAVE)
    finally:
        with _conectar_admin(postgres) as conexion:
            conexion.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(nombre))
            )


@pytest.fixture
def base_temporal_migrada(base_temporal: str) -> str:
    aplicar_migraciones(base_temporal)
    return base_temporal

