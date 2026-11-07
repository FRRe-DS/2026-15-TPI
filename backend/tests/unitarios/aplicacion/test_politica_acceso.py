"""Politica pura de acceso por rol y por conductor (US1 y US8).

Firmas bajo prueba:
    Identidad(roles, id_conductor=None, id_operador=None)
    verificar_acceso(identidad, id_conductor_recurso, admite) -> None
    verificar_rol(identidad, admite) -> None

`admite` es el conjunto de roles que la operacion permite. Con varios roles en el token
vale el que mas permite: un token de conductor y operador no queda limitado por el
`id_conductor` cuando la operacion admite al operador.
"""

import pytest
from app.aplicacion.politicas.acceso import (
    ROLES_ALTA_CONDUCTOR,
    ROLES_LISTAR_CONDUCTORES,
    Identidad,
    verificar_acceso,
    verificar_rol,
)
from app.dominio.errores import AccesoProhibido, RolNoAutorizado

LECTURA_CONDUCTOR = frozenset({"operador", "conductor", "servicio"})
ESCRITURA_CONDUCTOR = frozenset({"operador", "conductor"})


def identidad(*roles, id_conductor=None, id_operador=None):
    return Identidad(
        roles=frozenset(roles),
        id_conductor=id_conductor,
        id_operador=id_operador,
    )


# --- verificar_acceso: operador, conductor y servicio sobre un conductor ---


def test_el_operador_pasa_sin_id_conductor():
    verificar_acceso(identidad("operador", id_operador=3), 5, LECTURA_CONDUCTOR)


def test_el_conductor_pasa_sobre_su_propio_id():
    verificar_acceso(identidad("conductor", id_conductor=7), 7, LECTURA_CONDUCTOR)


def test_el_conductor_sobre_otro_id_lanza_acceso_prohibido():
    with pytest.raises(AccesoProhibido):
        verificar_acceso(identidad("conductor", id_conductor=7), 8, LECTURA_CONDUCTOR)


@pytest.mark.parametrize(
    "id_conductor",
    [None, True, False, "7", 7.0],
    ids=["nulo", "true", "false", "texto", "flotante"],
)
def test_el_conductor_sin_id_numerico_lanza_acceso_prohibido(id_conductor):
    with pytest.raises(AccesoProhibido):
        verificar_acceso(
            identidad("conductor", id_conductor=id_conductor),
            7,
            LECTURA_CONDUCTOR,
        )


def test_el_servicio_pasa_solo_si_la_operacion_lo_admite():
    verificar_acceso(identidad("servicio"), 7, LECTURA_CONDUCTOR)

    with pytest.raises(RolNoAutorizado):
        verificar_acceso(identidad("servicio"), 7, ESCRITURA_CONDUCTOR)


def test_un_rol_no_admitido_lanza_rol_no_autorizado():
    with pytest.raises(RolNoAutorizado):
        verificar_acceso(identidad("admin"), 7, LECTURA_CONDUCTOR)


def test_sin_roles_lanza_rol_no_autorizado():
    with pytest.raises(RolNoAutorizado):
        verificar_acceso(identidad(), 7, LECTURA_CONDUCTOR)


def test_el_conductor_con_rol_no_admitido_lanza_rol_no_autorizado():
    with pytest.raises(RolNoAutorizado):
        verificar_acceso(identidad("conductor", id_conductor=7), 7, {"servicio"})


# --- verificar_acceso: varios roles ---


@pytest.mark.parametrize(
    "roles",
    [("conductor", "operador"), ("operador", "conductor")],
    ids=["conductor-primero", "operador-primero"],
)
def test_operador_y_conductor_juntos_no_quedan_limitados_por_el_id(roles):
    verificar_acceso(identidad(*roles, id_conductor=7), 99, LECTURA_CONDUCTOR)


def test_conductor_y_servicio_pasa_por_el_rol_servicio_aunque_sea_otro_id():
    verificar_acceso(identidad("conductor", "servicio", id_conductor=7), 99, LECTURA_CONDUCTOR)


# --- verificar_rol: operaciones sin id de conductor ---


@pytest.mark.parametrize("rol", ["operador", "servicio"])
def test_listar_conductores_admite_operador_y_servicio(rol):
    verificar_rol(identidad(rol), ROLES_LISTAR_CONDUCTORES)


def test_listar_conductores_rechaza_al_conductor():
    with pytest.raises(RolNoAutorizado):
        verificar_rol(identidad("conductor", id_conductor=7), ROLES_LISTAR_CONDUCTORES)


@pytest.mark.parametrize("rol", ["operador", "conductor"])
def test_el_alta_de_conductor_admite_operador_y_conductor(rol):
    verificar_rol(identidad(rol), ROLES_ALTA_CONDUCTOR)


def test_el_alta_de_conductor_rechaza_al_servicio():
    with pytest.raises(RolNoAutorizado):
        verificar_rol(identidad("servicio"), ROLES_ALTA_CONDUCTOR)


def test_verificar_rol_pasa_si_alguno_de_varios_roles_esta_admitido():
    verificar_rol(identidad("conductor", "operador"), ROLES_LISTAR_CONDUCTORES)


def test_verificar_rol_sin_roles_lanza_rol_no_autorizado():
    with pytest.raises(RolNoAutorizado):
        verificar_rol(identidad(), ROLES_ALTA_CONDUCTOR)
