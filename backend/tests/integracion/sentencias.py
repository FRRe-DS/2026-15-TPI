"""Soporte para contar las sentencias SQL que emite un bloque de codigo."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, event


@contextmanager
def capturar_sentencias(engine: Engine) -> Iterator[list[str]]:
    """Registra todas las sentencias que el engine ejecuta dentro del bloque."""
    sentencias: list[str] = []

    def registrar(conexion, cursor, sentencia, parametros, contexto, ejecutar_muchos):
        sentencias.append(sentencia)

    event.listen(engine, "before_cursor_execute", registrar)
    try:
        yield sentencias
    finally:
        event.remove(engine, "before_cursor_execute", registrar)


def selects(sentencias: list[str]) -> list[str]:
    """Solo los SELECT: se ignoran SAVEPOINT, RELEASE, BEGIN, COMMIT, INSERT, etc."""
    return [s for s in sentencias if s.lstrip().upper().startswith("SELECT")]
