"""Validación local de los JWT emitidos por Keycloak."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWKClientError

from app.api.configuracion import Settings, obtener_configuracion
from app.api.errores import no_autenticado, sin_permisos

bearer_scheme = HTTPBearer(auto_error=False)

ROLES_VALIDOS = {"conductor", "operador"}


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
    settings: Annotated[Settings, Depends(obtener_configuracion)],
) -> PyJWKClient:
    """Obtiene el cliente JWKS correspondiente al realm configurado."""
    url = (
        f"{settings.KEYCLOAK_URL.rstrip('/')}"
        f"/realms/{settings.KEYCLOAK_REALM}"
        "/protocol/openid-connect/certs"
    )
    return _crear_cliente_jwks(url)


def _roles_del_payload(payload: dict[str, Any]) -> list[Any] | None:
    realm_access = payload.get("realm_access")
    if not isinstance(realm_access, dict):
        return None
    roles = realm_access.get("roles")
    return roles if isinstance(roles, list) else None


def requerir_usuario(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    settings: Annotated[Settings, Depends(obtener_configuracion)],
    jwks: Annotated[PyJWKClient, Depends(obtener_cliente_jwks)],
) -> dict[str, Any]:
    """Valida el JWT y exige al menos un rol reconocido."""
    if credentials is None:
        raise no_autenticado()

    token = credentials.credentials
    url_publica = settings.KEYCLOAK_PUBLIC_URL or settings.KEYCLOAK_URL
    emisor = f"{url_publica.rstrip('/')}/realms/{settings.KEYCLOAK_REALM}"

    try:
        signing_key = jwks.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=emisor,
            options={"require": ["exp", "iss"]},
        )
    except (jwt.PyJWTError, PyJWKClientError, ValueError, TypeError):
        raise no_autenticado() from None

    roles = _roles_del_payload(payload)
    if roles is None:
        raise sin_permisos("El usuario no tiene roles válidos")

    if not any(isinstance(rol, str) and rol in ROLES_VALIDOS for rol in roles):
        raise sin_permisos("El usuario no tiene un rol autorizado")

    return payload


def requerir_operador(
    usuario: Annotated[dict[str, Any], Depends(requerir_usuario)],
) -> dict[str, Any]:
    """Exige el rol operador y un ``id_operador`` numérico."""
    roles = _roles_del_payload(usuario) or []
    if "operador" not in roles:
        raise sin_permisos("Se requiere el rol operador para esta acción")

    id_operador = usuario.get("id_operador")
    # ``bool`` es subclase de ``int``, pero no es un identificador válido.
    if isinstance(id_operador, bool) or not isinstance(id_operador, int):
        raise sin_permisos("El operador debe tener un id_operador numérico")

    return usuario
