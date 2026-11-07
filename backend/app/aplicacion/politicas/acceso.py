"""Politica pura de acceso, sin dependencias de FastAPI ni de JWT.

Traduce la matriz de `specs/iteracion2-backend/contracts/token-jwt.md` a dos
verificaciones: una para operaciones sobre un conductor concreto (donde el rol
`conductor` queda limitado a su propio id) y otra para operaciones sin id de conductor.
"""

from collections.abc import Collection
from dataclasses import dataclass, field

from app.dominio.errores import AccesoProhibido, RolNoAutorizado

ROL_OPERADOR = "operador"
ROL_CONDUCTOR = "conductor"
ROL_SERVICIO = "servicio"

ROLES_LISTAR_CONDUCTORES = frozenset({ROL_OPERADOR, ROL_SERVICIO})
ROLES_ALTA_CONDUCTOR = frozenset({ROL_OPERADOR, ROL_CONDUCTOR})
ROLES_LECTURA_CONDUCTOR = frozenset({ROL_OPERADOR, ROL_CONDUCTOR, ROL_SERVICIO})
ROLES_ESCRITURA_CONDUCTOR = frozenset({ROL_OPERADOR, ROL_CONDUCTOR})
ROLES_SOLO_OPERADOR = frozenset({ROL_OPERADOR})


@dataclass(frozen=True)
class Identidad:
    roles: frozenset[str] = field(default_factory=frozenset)
    id_conductor: int | None = None
    id_operador: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "roles", frozenset(self.roles))


def verificar_acceso(
    identidad: Identidad,
    id_conductor_recurso: int,
    admite: Collection[str],
) -> None:
    """Autoriza una operacion sobre el conductor `id_conductor_recurso`.

    El operador y el servicio no tienen restriccion por conductor. El conductor solo
    pasa sobre su propio id y necesita un `id_conductor` entero en el token.
    """
    if ROL_OPERADOR in identidad.roles and ROL_OPERADOR in admite:
        return
    if ROL_SERVICIO in identidad.roles and ROL_SERVICIO in admite:
        return
    if ROL_CONDUCTOR in identidad.roles and ROL_CONDUCTOR in admite:
        _exigir_conductor_propio(identidad.id_conductor, id_conductor_recurso)
        return
    raise RolNoAutorizado("El rol del token no permite esta operacion")


def verificar_rol(identidad: Identidad, admite: Collection[str]) -> None:
    """Autoriza una operacion que no depende de un conductor concreto."""
    if any(rol in admite for rol in identidad.roles):
        return
    raise RolNoAutorizado("El rol del token no permite esta operacion")


def _exigir_conductor_propio(
    id_conductor: int | None,
    id_conductor_recurso: int,
) -> None:
    if not _es_entero(id_conductor):
        raise AccesoProhibido("El token del conductor no trae un id_conductor numerico")
    if id_conductor != id_conductor_recurso:
        raise AccesoProhibido("El conductor solo puede operar sobre sus propios datos")


def _es_entero(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)
