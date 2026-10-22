"""T078: bases separadas y aislamiento entre M3 y Keycloak (RNF-05)."""

from __future__ import annotations

from typing import Any

import psycopg
import pytest

pytestmark = pytest.mark.integration


def _conectar(datos: dict[str, Any], usuario: str, clave: str, base: str) -> psycopg.Connection:
    return psycopg.connect(
        host=datos["host"],
        port=datos["port"],
        user=usuario,
        password=clave,
        dbname=base,
        connect_timeout=3,
    )


def test_existen_las_bases_m3_y_keycloak(postgres: Any, datos_conexion: dict[str, Any]) -> None:
    with _conectar(
        datos_conexion, datos_conexion["superusuario"], datos_conexion["superclave"], "postgres"
    ) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT datname FROM pg_database WHERE datname = ANY(%s)",
                ([datos_conexion["m3_base"], datos_conexion["keycloak_base"]],),
            )
            bases = {fila[0] for fila in cursor.fetchall()}

    assert bases == {datos_conexion["m3_base"], datos_conexion["keycloak_base"]}


def test_cada_base_tiene_un_duenio_distinto(
    datos_conexion: dict[str, Any],
) -> None:
    with _conectar(
        datos_conexion, datos_conexion["superusuario"], datos_conexion["superclave"], "postgres"
    ) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT d.datname, r.rolname
                FROM pg_database d
                JOIN pg_roles r ON r.oid = d.datdba
                WHERE d.datname = ANY(%s)
                """,
                ([datos_conexion["m3_base"], datos_conexion["keycloak_base"]],),
            )
            duenios = dict(cursor.fetchall())

    assert duenios[datos_conexion["m3_base"]] == datos_conexion["m3_usuario"]
    assert duenios[datos_conexion["keycloak_base"]] == datos_conexion["keycloak_usuario"]
    assert duenios[datos_conexion["m3_base"]] != duenios[datos_conexion["keycloak_base"]]


def test_usuario_m3_puede_conectarse_a_su_base(datos_conexion: dict[str, Any]) -> None:
    with _conectar(
        datos_conexion,
        datos_conexion["m3_usuario"],
        datos_conexion["m3_clave"],
        datos_conexion["m3_base"],
    ) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT current_user, current_database()")
            usuario, base = cursor.fetchone()

    assert (usuario, base) == (datos_conexion["m3_usuario"], datos_conexion["m3_base"])


def test_usuario_m3_no_puede_conectarse_a_keycloak(
    datos_conexion: dict[str, Any],
) -> None:
    with pytest.raises(psycopg.OperationalError):
        with _conectar(
            datos_conexion,
            datos_conexion["m3_usuario"],
            datos_conexion["m3_clave"],
            datos_conexion["keycloak_base"],
        ):
            pass


def test_usuario_keycloak_no_puede_conectarse_a_m3(
    datos_conexion: dict[str, Any],
) -> None:
    with pytest.raises(psycopg.OperationalError):
        with _conectar(
            datos_conexion,
            datos_conexion["keycloak_usuario"],
            datos_conexion["keycloak_clave"],
            datos_conexion["m3_base"],
        ):
            pass
