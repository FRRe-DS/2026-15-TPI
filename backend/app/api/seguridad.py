
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWKClientError
from pydantic_settings import BaseSettings

from app.api.configuracion import Settings, obtener_configuracion


bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=8)
def _crear_cliente_jwks(url: str) -> PyJWKClient:
    """Crea un cliente JWKS con caché de claves."""
    return PyJWKClient(
        url,
        cache_jwk_set=True,
        lifespan=300,
        cache_keys=True,
        max_cached_keys=16,
        timeout=5,
    )


def obtener_cliente_jwks(
    settings: Settings = Depends(obtener_configuracion),
) -> PyJWKClient:
    """Obtiene el cliente JWKS correspondiente al realm configurado."""
    url = (
        f"{settings.KEYCLOAK_URL.rstrip('/')}"
        f"/realms/{settings.KEYCLOAK_REALM}"
        "/protocol/openid-connect/certs"
    )
    return _crear_cliente_jwks(url)


def _error_no_autorizado() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={
            "codigo": "NO_AUTORIZADO",
            "mensaje": "Token ausente o inválido",
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


def _error_prohibido(mensaje: str) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={
            "codigo": "PROHIBIDO",
            "mensaje": mensaje,
        },
    )


def requerir_usuario(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(obtener_configuracion),
    jwks: PyJWKClient = Depends(obtener_cliente_jwks),
) -> dict[str, Any]:
    """Valida el JWT y exige al menos un rol reconocido."""
    if credentials is None:
        raise _error_no_autorizado()

    token = credentials.credentials

    try:
        signing_key = jwks.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=(
                f"{settings.KEYCLOAK_URL.rstrip('/')}"
                f"/realms/{settings.KEYCLOAK_REALM}"
            ),
            options={
                "require": ["exp", "iss"],
            },
        )
    except (jwt.PyJWTError, PyJWKClientError, ValueError, TypeError):
        raise _error_no_autorizado() from None

    realm_access = payload.get("realm_access")
    roles = realm_access.get("roles") if isinstance(realm_access, dict) else None

    if not isinstance(roles, list):
        raise _error_prohibido("El usuario no tiene roles válidos")

    roles_validos = {"conductor", "operador"}
    if not any(
        isinstance(rol, str) and rol in roles_validos
        for rol in roles
    ):
        raise _error_prohibido("El usuario no tiene un rol autorizado")

    return payload


def requerir_operador(
    usuario: dict[str, Any] = Depends(requerir_usuario),
) -> dict[str, Any]:
    """Exige rol operador e identificador numérico."""
    realm_access = usuario.get("realm_access", {})
    roles = realm_access.get("roles", [])

    if "operador" not in roles:
        raise _error_prohibido(
            "Se requiere el rol operador para esta acción"
        )

    id_operador = usuario.get("id_operador")

    # bool es una subclase de int en Python, pero no es un ID válido.
    if isinstance(id_operador, bool) or not isinstance(id_operador, int):
        raise _error_prohibido(
            "El operador debe tener un id_operador numérico"
        )

    return usuario