
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def clave_rsa():
    """Genera una clave RSA exclusiva para las pruebas."""
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


@pytest.fixture(scope="session")
def jwks(clave_rsa) -> dict[str, Any]:
    """Publica la clave pública en formato JWKS."""
    public_key = clave_rsa.public_key()

    public_jwk = jwt.algorithms.RSAAlgorithm.to_jwk(
        public_key,
        as_dict=True,
    )

    public_jwk.update(
        {
            "kid": "test-key-1",
            "use": "sig",
            "alg": "RS256",
        }
    )

    return {"keys": [public_jwk]}


@pytest.fixture
def crear_token(clave_rsa):
    """
    Crea un JWT firmado para las pruebas.

    roles: lista de roles, por ejemplo ["operador"].
    id_operador: identificador numérico opcional.
    exp: timestamp Unix, datetime o None.
    iss: emisor del token.
    """
    def _crear_token(
        roles=None,
        id_operador=None,
        exp=None,
        iss="http://localhost:8080/realms/m3",
    ):
        ahora = datetime.now(timezone.utc)

        if exp is None:
            expiracion = ahora + timedelta(minutes=15)
        elif isinstance(exp, datetime):
            expiracion = exp
        else:
            expiracion = exp

        payload = {
            "iss": iss,
            "iat": int(ahora.timestamp()),
            "exp": expiracion,
            "realm_access": {
                "roles": roles if roles is not None else ["conductor"]
            },
        }

        if id_operador is not None:
            payload["id_operador"] = id_operador

        return jwt.encode(
            payload,
            clave_rsa,
            algorithm="RS256",
            headers={"kid": "test-key-1"},
        )

    return _crear_token


from app.main import app
from app.api.seguridad import (
    obtener_cliente_jwks,
    requerir_usuario,
    requerir_operador,
)


@pytest.fixture
def client(clave_rsa, jwks, monkeypatch):
    """Cliente HTTP con autenticación y casos de uso simulados."""

    class ClienteJWKSTest:
        def get_signing_key_from_jwt(self, token):
            import jwt

            encabezado = jwt.get_unverified_header(token)

            if encabezado.get("kid") != "test-key-1":
                raise jwt.exceptions.PyJWKClientError(
                    "Clave de prueba desconocida"
                )

            return type(
                "SigningKey",
                (),
                {"key": clave_rsa.public_key()},
            )()

    cliente_jwks = ClienteJWKSTest()

    app.dependency_overrides[obtener_cliente_jwks] = (
        lambda: cliente_jwks
    )
    monkeypatch.setenv(
    "KEYCLOAK_URL",
    "http://localhost:8080",
    )
    monkeypatch.setenv("KEYCLOAK_REALM", "m3")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/test",
    )
    # Evita que los tests hereden overrides de otra prueba.
    app.dependency_overrides.pop(requerir_usuario, None)
    app.dependency_overrides.pop(requerir_operador, None)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

