"""Validación local de los JWT emitidos por Keycloak."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWKClientError

from app.api.configuracion import Settings, obtener_configuracion
from app.api.errores import no_autenticado, sin_permisos
from app.aplicacion.politicas.acceso import (
    ROL_CONDUCTOR,
    ROL_OPERADOR,
    ROL_SERVICIO,
    ROLES_ALTA_CONDUCTOR,
    ROLES_ESCRITURA_CONDUCTOR,
    ROLES_LECTURA_CONDUCTOR,
    ROLES_LISTAR_CONDUCTORES,
    Identidad,
    es_entero,
    verificar_acceso,
    verificar_rol,
)

bearer_scheme = HTTPBearer(auto_error=False)

ROLES_VALIDOS = {ROL_CONDUCTOR, ROL_OPERADOR, ROL_SERVICIO}


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
    if not es_entero(id_operador):
        raise sin_permisos("El operador debe tener un id_operador numérico")

    return usuario


def _entero_o_none(valor: Any) -> int | None:
    return valor if es_entero(valor) else None


def identidad_del_payload(payload: dict[str, Any]) -> Identidad:
    """Construye la identidad con los roles reconocidos y los ids enteros."""
    roles = _roles_del_payload(payload) or []
    return Identidad(
        roles=frozenset(rol for rol in roles if isinstance(rol, str) and rol in ROLES_VALIDOS),
        id_conductor=_entero_o_none(payload.get("id_conductor")),
        id_operador=_entero_o_none(payload.get("id_operador")),
    )


def requerir_identidad(
    usuario: Annotated[dict[str, Any], Depends(requerir_usuario)],
) -> Identidad:
    """Valida el token y entrega la identidad de quien llama."""
    return identidad_del_payload(usuario)


def requerir_operador_o_servicio(
    identidad: Annotated[Identidad, Depends(requerir_identidad)],
) -> Identidad:
    """Operaciones sin conductor concreto: solo operador o servicio."""
    verificar_rol(identidad, ROLES_LISTAR_CONDUCTORES)
    return identidad


def requerir_operador_o_conductor(
    identidad: Annotated[Identidad, Depends(requerir_identidad)],
) -> Identidad:
    """Alta de conductor: operador o conductor; servicio no da altas."""
    verificar_rol(identidad, ROLES_ALTA_CONDUCTOR)
    return identidad


def requerir_conductor_propio_u_operador(
    id_conductor: Annotated[int, Path()],
    identidad: Annotated[Identidad, Depends(requerir_identidad)],
) -> Identidad:
    """Escrituras sobre un conductor: operador, o el conductor sobre sí mismo."""
    verificar_acceso(identidad, id_conductor, ROLES_ESCRITURA_CONDUCTOR)
    return identidad


def requerir_conductor_propio_operador_o_servicio(
    id_conductor: Annotated[int, Path()],
    identidad: Annotated[Identidad, Depends(requerir_identidad)],
) -> Identidad:
    """Lecturas sobre un conductor: operador, servicio o el propio conductor."""
    verificar_acceso(identidad, id_conductor, ROLES_LECTURA_CONDUCTOR)
    return identidad
