"""T084: el seed es idempotente y cubre los escenarios de prueba."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import create_engine, text


def test_el_seed_declara_licencias_vigentes_y_vencidas(seed_module: Any) -> None:
    estados = {documento["estado"] for documento in seed_module.DOCUMENTOS}
    assert {"VIGENTE", "VENCIDO"} <= estados


def test_el_seed_declara_un_conductor_conectado_y_disponible(seed_module: Any) -> None:
    assert any(
        conductor["conectado"] and conductor["disponible"] for conductor in seed_module.CONDUCTORES
    )


def test_el_seed_declara_alta_para_cada_conductor_y_vehiculo(seed_module: Any) -> None:
    altas_conductor = {
        evento["dni_conductor"]
        for evento in seed_module.EVENTOS_CONDUCTOR
        if evento["accion"] == "ALTA"
    }
    altas_vehiculo = {
        evento["patente"] for evento in seed_module.EVENTOS_VEHICULO if evento["accion"] == "ALTA"
    }

    assert altas_conductor == {conductor["dni"] for conductor in seed_module.CONDUCTORES}
    assert altas_vehiculo == {vehiculo["patente"] for vehiculo in seed_module.VEHICULOS}


def test_el_seed_es_determinista_en_sus_claves_naturales(seed_module: Any) -> None:
    assert len({c["dni"] for c in seed_module.CONDUCTORES}) == len(seed_module.CONDUCTORES)
    assert len({v["patente"] for v in seed_module.VEHICULOS}) == len(seed_module.VEHICULOS)
    assert len({d["numero"] for d in seed_module.DOCUMENTOS}) == len(seed_module.DOCUMENTOS)


@pytest.mark.integration
def test_seed_idempotente_y_completo(base_temporal_migrada: str, seed_module: Any) -> None:
    primero = seed_module.cargar_datos(base_temporal_migrada)
    segundo = seed_module.cargar_datos(base_temporal_migrada)

    assert primero == segundo

    engine = create_engine(base_temporal_migrada)
    try:
        with engine.connect() as conexion:
            assert conexion.execute(text("SELECT count(*) FROM conductor")).scalar_one() == len(
                seed_module.CONDUCTORES
            )
            assert conexion.execute(text("SELECT count(*) FROM vehiculo")).scalar_one() == len(
                seed_module.VEHICULOS
            )
            assert conexion.execute(
                text("SELECT count(*) FROM documento_conductor")
            ).scalar_one() == len(seed_module.DOCUMENTOS)
            assert (
                conexion.execute(text("SELECT count(*) FROM vehiculo_tipo_servicio")).scalar_one()
                >= 1
            )

            licencias = {
                fila[0]
                for fila in conexion.execute(
                    text(
                        """
                        SELECT estado
                        FROM documento_conductor
                        WHERE tipo = 'LICENCIA'
                        """
                    )
                )
            }
            assert {"VIGENTE", "VENCIDO"} <= licencias

            conectado_disponible = conexion.execute(
                text(
                    """
                    SELECT count(*)
                    FROM conductor
                    WHERE conectado IS TRUE AND disponible IS TRUE
                    """
                )
            ).scalar_one()
            assert conectado_disponible >= 1

            conductores_sin_alta = conexion.execute(
                text(
                    """
                    SELECT c.id_conductor
                    FROM conductor c
                    LEFT JOIN habilitacion_evento_conductor e
                      ON e.id_conductor = c.id_conductor AND e.accion = 'ALTA'
                    GROUP BY c.id_conductor
                    HAVING count(e.id_evento) = 0
                    """
                )
            ).all()
            vehiculos_sin_alta = conexion.execute(
                text(
                    """
                    SELECT v.id_vehiculo
                    FROM vehiculo v
                    LEFT JOIN habilitacion_evento_vehiculo e
                      ON e.id_vehiculo = v.id_vehiculo AND e.accion = 'ALTA'
                    GROUP BY v.id_vehiculo
                    HAVING count(e.id_evento) = 0
                    """
                )
            ).all()

            assert conductores_sin_alta == []
            assert vehiculos_sin_alta == []

            dnis = conexion.execute(text("SELECT dni FROM conductor")).scalars().all()
            patentes = conexion.execute(text("SELECT patente FROM vehiculo")).scalars().all()
            assert len(dnis) == len(set(dnis))
            assert len(patentes) == len(set(patentes))
    finally:
        engine.dispose()
