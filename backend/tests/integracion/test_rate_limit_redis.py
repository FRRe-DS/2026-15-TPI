from __future__ import annotations

import os
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from app.api.errores import ErrorAPI
from app.api.rate_limit import RedisRateLimiter
from redis import Redis
from redis.exceptions import RedisError

pytestmark = pytest.mark.integration
SECRETO_HMAC_PRUEBAS = "integration-hmac-secret-shared-by-all-api-instances"


@pytest.fixture
def clientes_redis() -> Iterator[tuple[Redis, Redis]]:
    url = os.getenv("RATE_LIMIT_TEST_REDIS_URL", "redis://localhost:6379/0")
    password = os.getenv("RATE_LIMIT_TEST_REDIS_PASSWORD") or None
    clientes = (
        Redis.from_url(url, password=password, decode_responses=True),
        Redis.from_url(url, password=password, decode_responses=True),
    )
    try:
        for cliente in clientes:
            cliente.ping()
    except RedisError as error:
        for cliente in clientes:
            cliente.close()
        pytest.skip(f"Se requiere un Redis de integración disponible: {type(error).__name__}")

    yield clientes

    for cliente in clientes:
        cliente.close()


def test_cuota_se_comparte_entre_clientes_redis(clientes_redis: tuple[Redis, Redis]) -> None:
    identidad = f"compartida-{uuid4().hex}"
    primero, segundo = (
        RedisRateLimiter(cliente, SECRETO_HMAC_PRUEBAS) for cliente in clientes_redis
    )
    primero.verificar(
        scope="jwt",
        identidad=identidad,
        limite=1,
        ventana_segundos=10,
    )

    with pytest.raises(ErrorAPI) as error:
        segundo.verificar(
            scope="jwt",
            identidad=identidad,
            limite=1,
            ventana_segundos=10,
        )

    assert error.value.status_code == 429


def test_cuotas_concurrentes_respetan_el_limite_atomico(
    clientes_redis: tuple[Redis, Redis],
) -> None:
    identidad = f"concurrente-{uuid4().hex}"
    limitadores = tuple(
        RedisRateLimiter(cliente, SECRETO_HMAC_PRUEBAS) for cliente in clientes_redis
    )

    def solicitar(indice: int) -> bool:
        try:
            limitadores[indice % len(limitadores)].verificar(
                scope="ip",
                identidad=identidad,
                limite=10,
                ventana_segundos=10,
            )
        except ErrorAPI as error:
            assert error.status_code == 429
            return False
        return True

    with ThreadPoolExecutor(max_workers=20) as executor:
        resultados = list(executor.map(solicitar, range(20)))

    assert sum(resultados) == 10


def test_cuota_se_libera_al_expirar_la_ventana(clientes_redis: tuple[Redis, Redis]) -> None:
    identidad = f"expiracion-{uuid4().hex}"
    limitador = RedisRateLimiter(clientes_redis[0], SECRETO_HMAC_PRUEBAS)
    argumentos = {
        "scope": "jwt",
        "identidad": identidad,
        "limite": 1,
        "ventana_segundos": 1,
    }

    limitador.verificar(**argumentos)
    with pytest.raises(ErrorAPI):
        limitador.verificar(**argumentos)

    time.sleep(1.1)
    limitador.verificar(**argumentos)
