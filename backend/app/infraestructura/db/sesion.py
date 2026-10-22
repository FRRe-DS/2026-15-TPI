"""Creación perezosa de engines y sesiones.

La configuración se toma exclusivamente de ``DATABASE_URL`` para cumplir
RNF-06. No se crea ningún engine al importar el módulo.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

_VARIABLE = "DATABASE_URL"


def obtener_database_url() -> str:
    """Devuelve la URL configurada o falla con un mensaje accionable."""

    url = os.environ.get(_VARIABLE, "").strip()
    if not url:
        raise RuntimeError(
            "Falta la variable de entorno DATABASE_URL. "
            "Configurala con el formato postgresql+psycopg://usuario:clave@host:5432/base."
        )
    if not url.startswith(("postgresql+psycopg://", "postgresql+psycopg2://")):
        raise RuntimeError(
            "DATABASE_URL debe usar el driver psycopg, por ejemplo "
            "postgresql+psycopg://usuario:clave@host:5432/base."
        )
    return url


def crear_engine(database_url: str | None = None, *, echo: bool = False) -> Engine:
    """Crea un engine de SQLAlchemy con verificación de conexión previa."""

    return create_engine(database_url or obtener_database_url(), echo=echo, pool_pre_ping=True)


def crear_sessionmaker(engine: Engine | None = None) -> sessionmaker[Session]:
    """Crea una fábrica de sesiones ligada al engine indicado."""

    return sessionmaker(bind=engine or crear_engine(), expire_on_commit=False)


@contextmanager
def sesion(engine: Engine | None = None) -> Iterator[Session]:
    """Entrega una sesión transaccional y garantiza su cierre."""

    factory = crear_sessionmaker(engine)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
