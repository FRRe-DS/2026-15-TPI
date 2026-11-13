from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

EMISOR_VALIDO = "http://localhost:8080/realms/m3"
KID_PRUEBA = "test-key-1"
SUJETO_PRUEBA = "usuario-de-prueba"
VARIABLES_ENTORNO = {
    "KEYCLOAK_URL": "http://localhost:8080",
    "KEYCLOAK_PUBLIC_URL": "http://localhost:8080",
    "KEYCLOAK_REALM": "m3",
    "RATE_LIMIT_HMAC_SECRET": "test-hmac-secret-shared-by-all-api-tests",
    "DATABASE_URL": "postgresql+psycopg://test:test@localhost:5432/test",
}


@pytest.fixture
def entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable, valor in VARIABLES_ENTORNO.items():
        monkeypatch.setenv(variable, valor)


@pytest.fixture(scope="session")
def clave_rsa() -> rsa.RSAPrivateKey:
    """Genera una clave RSA exclusiva para las pruebas."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def jwks(clave_rsa: rsa.RSAPrivateKey) -> dict[str, Any]:
    """Publica la clave pública en formato JWKS."""
    public_jwk = jwt.algorithms.RSAAlgorithm.to_jwk(
        clave_rsa.public_key(),
        as_dict=True,
    )
    public_jwk.update({"kid": KID_PRUEBA, "use": "sig", "alg": "RS256"})
    return {"keys": [public_jwk]}


@pytest.fixture(scope="session")
def cliente_jwks(clave_rsa: rsa.RSAPrivateKey) -> SimpleNamespace:
    """Cliente JWKS falso que entrega la clave pública de prueba."""

    def get_signing_key_from_jwt(token: str) -> SimpleNamespace:
        encabezado = jwt.get_unverified_header(token)
        if encabezado.get("kid") != KID_PRUEBA:
            raise jwt.exceptions.PyJWKClientError("Clave de prueba desconocida")
        return SimpleNamespace(key=clave_rsa.public_key())

    return SimpleNamespace(get_signing_key_from_jwt=get_signing_key_from_jwt)


@pytest.fixture
def crear_token(clave_rsa: rsa.RSAPrivateKey):
    """Crea un JWT firmado con la clave de prueba."""

    def _crear_token(
        roles: list[str] | None = None,
        id_operador: Any = None,
        exp: datetime | int | None = None,
        iss: str = EMISOR_VALIDO,
        kid: str = KID_PRUEBA,
        id_conductor: Any = None,
        sub: str = SUJETO_PRUEBA,
    ) -> str:
        ahora = datetime.now(UTC)
        expiracion = exp if exp is not None else ahora + timedelta(minutes=15)
        payload: dict[str, Any] = {
            "iss": iss,
            "sub": sub,
            "iat": int(ahora.timestamp()),
            "exp": expiracion,
            "realm_access": {
                "roles": roles if roles is not None else ["conductor"],
            },
        }
        if id_operador is not None:
            payload["id_operador"] = id_operador
        if id_conductor is not None:
            payload["id_conductor"] = id_conductor
        return jwt.encode(
            payload,
            clave_rsa,
            algorithm="RS256",
            headers={"kid": kid},
        )

    return _crear_token


@pytest.fixture
def headers_conductor(crear_token) -> dict[str, str]:
    token = crear_token(roles=["conductor"], id_conductor=1)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def headers_servicio(crear_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token(roles=['servicio'])}"}


@pytest.fixture
def headers_conductor_de(crear_token):
    """Fabrica los headers de un conductor con el ``id_conductor`` indicado."""

    def _headers(id_conductor: int) -> dict[str, str]:
        token = crear_token(roles=["conductor"], id_conductor=id_conductor)
        return {"Authorization": f"Bearer {token}"}

    return _headers


@pytest.fixture
def headers_operador(crear_token) -> dict[str, str]:
    token = crear_token(roles=["operador"], id_operador=7)
    return {"Authorization": f"Bearer {token}"}
