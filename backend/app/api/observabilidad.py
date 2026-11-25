"""Duraciones de negocio desde la recepción HTTP hasta el retorno del caso de uso."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from os import getenv
from time import perf_counter

from opentelemetry import metrics
from starlette.types import ASGIApp, Receive, Scope, Send

recepcion: ContextVar[float | None] = ContextVar("m3_recepcion", default=None)


def habilitada() -> bool:
    return getenv("M3_OTEL_ENABLED", "false").lower() == "true"


class InicioSolicitud:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        token = recepcion.set(perf_counter())
        try:
            await self.app(scope, receive, send)
        finally:
            recepcion.reset(token)


@contextmanager
def medir_operacion(operacion: str, *, enabled: bool = True) -> Iterator[None]:
    if not enabled or not habilitada():
        yield
        return
    histograma = metrics.get_meter("utn.frre.m3.grupo15.business").create_histogram(
        f"m3.driver.{operacion}.duration", unit="s"
    )
    inicio = recepcion.get()
    if inicio is None:
        inicio = perf_counter()
    outcome = "error"
    try:
        yield
        outcome = "success"
    finally:
        histograma.record(perf_counter() - inicio, {"outcome": outcome})
