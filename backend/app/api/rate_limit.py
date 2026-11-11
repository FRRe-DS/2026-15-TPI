"""Rate limiting distribuido basado en una ventana deslizante de Redis."""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Protocol
from uuid import uuid4

from redis.exceptions import RedisError

from app.api.errores import limite_de_solicitudes, servicio_temporalmente_no_disponible

logger = logging.getLogger(__name__)


class RedisEvalClient(Protocol):
    def eval(self, script: str, numkeys: int, *keys_and_args: str | int) -> list[int]: ...


_SCRIPT_VENTANA_DESLIZANTE = """
local instante = redis.call('TIME')
local ahora = instante[1] * 1000 + math.floor(instante[2] / 1000)
local ventana = tonumber(ARGV[2])
local limite = tonumber(ARGV[1])
local desde = ahora - ventana

redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', desde)
local cantidad = redis.call('ZCARD', KEYS[1])

if cantidad >= limite then
    local mas_antiguo = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    local reintento = math.ceil((tonumber(mas_antiguo[2]) + ventana - ahora) / 1000)
    if reintento < 1 then
        reintento = 1
    end
    return {0, reintento}
end

redis.call('ZADD', KEYS[1], ahora, ARGV[3])
redis.call('PEXPIRE', KEYS[1], ventana)
return {1, 0}
"""


class RedisRateLimiter:
    """Evalúa cuotas compartidas sin almacenar la identidad en claro."""

    def __init__(self, cliente: RedisEvalClient, secreto_hmac: str) -> None:
        self._cliente = cliente
        self._secreto_hmac = secreto_hmac.encode("utf-8")
        if len(self._secreto_hmac) < 32:
            raise ValueError("El secreto HMAC de rate limiting debe tener al menos 32 bytes")

    def verificar(
        self,
        *,
        scope: str,
        identidad: str,
        limite: int,
        ventana_segundos: int,
    ) -> None:
        digest = hmac.new(
            self._secreto_hmac,
            identidad.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        clave = f"m3:rate-limit:v1:{scope}:{digest}"

        try:
            resultado = self._cliente.eval(
                _SCRIPT_VENTANA_DESLIZANTE,
                1,
                clave,
                limite,
                ventana_segundos * 1000,
                uuid4().hex,
            )
        except RedisError as error:
            logger.warning(
                "Redis no disponible para rate limiting (%s)",
                type(error).__name__,
            )
            raise servicio_temporalmente_no_disponible() from None

        if not isinstance(resultado, (list, tuple)) or len(resultado) != 2:
            raise RuntimeError("Redis devolvió una respuesta inválida al limitar solicitudes")

        permitido, reintento = (int(valor) for valor in resultado)
        if permitido == 0:
            raise limite_de_solicitudes(reintento)
