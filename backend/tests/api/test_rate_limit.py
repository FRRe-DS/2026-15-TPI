from __future__ import annotations

import hashlib
import hmac
from collections import defaultdict
from math import ceil

import pytest
from app.api.errores import ErrorAPI, limite_de_solicitudes
from app.api.main import crear_app
from app.api.rate_limit import RedisRateLimiter
from app.api.seguridad import obtener_cliente_jwks, obtener_rate_limiter
from fastapi import APIRouter
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError

SECRETO_HMAC_PRUEBAS = "test-hmac-secret-shared-by-all-api-tests"


class RedisFalso:
    def __init__(self) -> None:
        self.ahora_ms = 100_000
        self.eventos: dict[str, list[tuple[int, str]]] = defaultdict(list)
        self.expira_en: dict[str, int] = {}
        self.error: Exception | None = None

    def eval(
        self,
        _script: str,
        _cantidad_claves: int,
        *argumentos: str | int,
    ) -> list[int]:
        if self.error is not None:
            raise self.error

        clave = str(argumentos[0])
        limite = int(argumentos[1])
        ventana_ms = int(argumentos[2])
        miembro = str(argumentos[3])
        corte = self.ahora_ms - ventana_ms
        eventos = [evento for evento in self.eventos[clave] if evento[0] > corte]
        self.eventos[clave] = eventos

        if len(eventos) >= limite:
            restante_ms = eventos[0][0] + ventana_ms - self.ahora_ms
            return [0, max(1, ceil(restante_ms / 1000))]

        eventos.append((self.ahora_ms, miembro))
        self.expira_en[clave] = self.ahora_ms + ventana_ms
        return [1, 0]


class LimitadorCaptura:
    def __init__(self) -> None:
        self.llamadas: list[dict[str, str | int]] = []

    def verificar(self, **argumentos: str | int) -> None:
        self.llamadas.append(argumentos)


def _limitar(
    redis: RedisFalso,
    secreto_hmac: str = SECRETO_HMAC_PRUEBAS,
) -> RedisRateLimiter:
    return RedisRateLimiter(redis, secreto_hmac)


def _verificar(
    limitador: RedisRateLimiter,
    identidad: str = "usuario-1",
    *,
    scope: str = "jwt",
    limite: int = 3,
    ventana: int = 60,
) -> None:
    limitador.verificar(
        scope=scope,
        identidad=identidad,
        limite=limite,
        ventana_segundos=ventana,
    )


def test_permite_hasta_el_limite_y_luego_responde_429() -> None:
    redis = RedisFalso()
    limitador = _limitar(redis)

    for _ in range(3):
        _verificar(limitador)

    with pytest.raises(ErrorAPI) as error:
        _verificar(limitador)

    assert error.value.status_code == 429
    assert error.value.codigo == "LIMITE_DE_SOLICITUDES"
    assert error.value.headers == {"Retry-After": "60", "Cache-Control": "no-store"}


def test_ventana_deslizante_permite_otra_solicitud_al_expirar_el_evento() -> None:
    redis = RedisFalso()
    limitador = _limitar(redis)
    _verificar(limitador, limite=1)

    redis.ahora_ms += 60_001

    _verificar(limitador, limite=1)


def test_evento_en_el_borde_exacto_de_la_ventana_ya_esta_expirado() -> None:
    redis = RedisFalso()
    limitador = _limitar(redis)
    _verificar(limitador, limite=2)
    redis.ahora_ms += 1
    _verificar(limitador, limite=2)
    redis.ahora_ms += 59_999

    _verificar(limitador, limite=2)


def test_retry_after_se_redondea_hacia_arriba_sin_extender_ventana() -> None:
    redis = RedisFalso()
    limitador = _limitar(redis)
    _verificar(limitador, limite=1)
    expiracion_original = next(iter(redis.expira_en.values()))
    redis.ahora_ms += 58_501

    with pytest.raises(ErrorAPI) as error:
        _verificar(limitador, limite=1)

    assert error.value.headers is not None
    assert error.value.headers["Retry-After"] == "2"
    assert next(iter(redis.expira_en.values())) == expiracion_original


def test_solicitud_denegada_no_se_agrega_al_contador() -> None:
    redis = RedisFalso()
    limitador = _limitar(redis)
    _verificar(limitador, limite=1)
    cantidad_antes = len(next(iter(redis.eventos.values())))

    with pytest.raises(ErrorAPI):
        _verificar(limitador, limite=1)

    assert len(next(iter(redis.eventos.values()))) == cantidad_antes


def test_identidad_y_scope_generan_cuotas_separadas() -> None:
    redis = RedisFalso()
    limitador = _limitar(redis)
    _verificar(limitador, identidad="issuer\0usuario-1", limite=1)
    _verificar(limitador, identidad="issuer\0usuario-2", limite=1)
    _verificar(limitador, identidad="issuer\0usuario-1", scope="ip", limite=1)

    assert len(redis.eventos) == 3


def test_clave_redis_usa_hmac_versionado_y_no_expone_la_identidad() -> None:
    redis = RedisFalso()
    identidad = "http://issuer/realm\0usuario"
    digest = hmac.new(
        SECRETO_HMAC_PRUEBAS.encode("utf-8"),
        identidad.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    _verificar(_limitar(redis), identidad=identidad)

    assert list(redis.eventos) == [f"m3:rate-limit:v1:jwt:{digest}"]
    assert identidad not in next(iter(redis.eventos))


def test_secretos_hmac_distintos_generan_cuotas_distintas() -> None:
    redis = RedisFalso()
    identidad = "192.0.2.10"

    _verificar(_limitar(redis, SECRETO_HMAC_PRUEBAS), identidad, scope="ip", limite=1)
    _verificar(
        _limitar(redis, "different-test-hmac-secret-shared-across-instances"),
        identidad,
        scope="ip",
        limite=1,
    )

    assert len(redis.eventos) == 2


def test_secreto_hmac_debe_tener_al_menos_32_bytes() -> None:
    with pytest.raises(ValueError, match="al menos 32 bytes"):
        _limitar(RedisFalso(), "demasiado corto")


def test_error_redis_responde_503_sin_exponer_detalles() -> None:
    redis = RedisFalso()
    redis.error = ConnectionError("redis-secret debe permanecer oculto")

    with pytest.raises(ErrorAPI) as error:
        _verificar(_limitar(redis))

    assert error.value.status_code == 503
    assert error.value.codigo == "SERVICIO_TEMPORALMENTE_NO_DISPONIBLE"
    assert "redis-secret" not in error.value.mensaje


@pytest.fixture
def client_y_limitador(
    cliente_jwks,
    entorno: None,
) -> tuple[TestClient, LimitadorCaptura]:
    router = APIRouter()

    @router.get("/protegido")
    def protegido() -> dict[str, bool]:
        return {"ok": True}

    limitador = LimitadorCaptura()
    app = crear_app(routers=[router])
    app.dependency_overrides[obtener_cliente_jwks] = lambda: cliente_jwks
    app.dependency_overrides[obtener_rate_limiter] = lambda: limitador
    with TestClient(app) as client:
        yield client, limitador
    app.dependency_overrides.clear()


def test_solicitud_sin_jwt_se_limita_por_ip(
    client_y_limitador: tuple[TestClient, LimitadorCaptura],
) -> None:
    client, limitador = client_y_limitador

    respuesta = client.get("/api/v1/protegido")

    assert respuesta.status_code == 401
    assert limitador.llamadas == [
        {
            "scope": "ip",
            "identidad": "testclient",
            "limite": 60,
            "ventana_segundos": 60,
        }
    ]


def test_jwt_verificado_se_limita_por_issuer_y_subject(
    client_y_limitador: tuple[TestClient, LimitadorCaptura],
    crear_token,
) -> None:
    client, limitador = client_y_limitador
    token = crear_token(sub="subject-verificado")

    respuesta = client.get(
        "/api/v1/protegido",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    assert limitador.llamadas == [
        {
            "scope": "preauth-ip",
            "identidad": "testclient",
            "limite": 1000,
            "ventana_segundos": 60,
        },
        {
            "scope": "jwt",
            "identidad": "http://localhost:8080/realms/m3\0subject-verificado",
            "limite": 120,
            "ventana_segundos": 60,
        },
    ]


def test_jwt_sin_subject_no_vacio_se_limita_por_ip_y_se_rechaza(
    client_y_limitador: tuple[TestClient, LimitadorCaptura],
    crear_token,
) -> None:
    client, limitador = client_y_limitador
    token = crear_token(sub=" ")

    respuesta = client.get(
        "/api/v1/protegido",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 401
    assert [llamada["scope"] for llamada in limitador.llamadas] == ["preauth-ip", "ip"]


def test_cuota_preliminar_rechaza_antes_de_consultar_jwks(
    cliente_jwks,
    entorno: None,
    crear_token,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    consultas_jwks = 0

    def consultar_jwks(_token: str) -> None:
        nonlocal consultas_jwks
        consultas_jwks += 1

    monkeypatch.setattr(cliente_jwks, "get_signing_key_from_jwt", consultar_jwks)

    class LimitadorPreautenticacionRechazante:
        def verificar(self, *, scope: str, **_argumentos: str | int) -> None:
            if scope == "preauth-ip":
                raise limite_de_solicitudes(1)

    router = APIRouter()

    @router.get("/protegido")
    def protegido() -> dict[str, bool]:
        return {"ok": True}

    app = crear_app(routers=[router])
    app.dependency_overrides[obtener_cliente_jwks] = lambda: cliente_jwks
    app.dependency_overrides[obtener_rate_limiter] = LimitadorPreautenticacionRechazante
    token = crear_token()
    with TestClient(app) as client:
        respuesta = client.get(
            "/api/v1/protegido",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert respuesta.status_code == 429
    assert consultas_jwks == 0
