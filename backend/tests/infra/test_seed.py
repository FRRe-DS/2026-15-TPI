"""T084: el seed es idempotente y cubre los escenarios de prueba."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import create_engine, text


def test_el_seed_declara_licencias_vigentes_y_vencidas(seed_module: Any) -> None:
    hoy = seed_module.FECHA_BASE.date()
    vencimientos = [documento["fecha_vencimiento"] for documento in seed_module.DOCUMENTOS]

    assert any(vencimiento < hoy for vencimiento in vencimientos)
    assert any(vencimiento >= hoy for vencimiento in vencimientos)
    assert all(
        documento["fecha_emision"] < documento["fecha_vencimiento"]
        for documento in seed_module.DOCUMENTOS
    )
    assert all("estado" not in documento for documento in seed_module.DOCUMENTOS)


def test_los_eventos_alta_tienen_motivo_no_vacio(seed_module: Any) -> None:
    eventos = [*seed_module.EVENTOS_CONDUCTOR, *seed_module.EVENTOS_VEHICULO]
    altas = [evento for evento in eventos if evento["accion"] == "ALTA"]

    assert altas
    assert all(isinstance(evento["motivo"], str) and evento["motivo"].strip() for evento in altas)


def test_el_historial_de_habilitacion_encadena_estados(seed_module: Any) -> None:
    conductores = {conductor["dni"]: conductor for conductor in seed_module.CONDUCTORES}
    por_conductor: dict[str, list[dict[str, Any]]] = {}
    for evento in seed_module.EVENTOS_CONDUCTOR:
        por_conductor.setdefault(evento["dni_conductor"], []).append(evento)

    for dni, eventos in por_conductor.items():
        anterior = None
        for evento in eventos:
            assert evento["estado_anterior"] == anterior
            anterior = evento["estado_nuevo"]
        assert anterior == conductores[dni]["estado_habilitacion"]

    vehiculos = {vehiculo["patente"]: vehiculo for vehiculo in seed_module.VEHICULOS}
    por_vehiculo: dict[str, list[dict[str, Any]]] = {}
    for evento in seed_module.EVENTOS_VEHICULO:
        por_vehiculo.setdefault(evento["patente"], []).append(evento)

    for patente, eventos in por_vehiculo.items():
        anterior = None
        for evento in eventos:
            assert evento["estado_anterior"] == anterior
            anterior = evento["estado_nuevo"]
        assert anterior == vehiculos[patente]["estado_habilitacion"]


def test_el_seed_declara_un_conductor_disponible(seed_module: Any) -> None:
    assert any(conductor["estado"] == "DISPONIBLE" for conductor in seed_module.CONDUCTORES)


def test_el_seed_cubre_los_cuatro_estados_operativos(seed_module: Any) -> None:
    estados = {conductor["estado"] for conductor in seed_module.CONDUCTORES}

    assert estados == {"DESCONECTADO", "CONECTADO", "DISPONIBLE", "OCUPADO"}


def test_el_seed_incluye_conductores_sin_ubicacion_y_sin_vehiculo_activo(
    seed_module: Any,
) -> None:
    sin_ubicacion = [
        conductor
        for conductor in seed_module.CONDUCTORES
        if conductor["latitud"] is None
        and conductor["longitud"] is None
        and conductor["fecha_act_ubic"] is None
    ]
    sin_vehiculo = [
        conductor
        for conductor in seed_module.CONDUCTORES
        if conductor["dni"] not in seed_module.VEHICULO_ACTIVO
    ]

    assert sin_ubicacion
    assert sin_vehiculo


def test_el_seed_incluye_conductores_con_y_sin_calificaciones(seed_module: Any) -> None:
    con_calificaciones = [
        conductor
        for conductor in seed_module.CONDUCTORES
        if conductor["cantidad_calificaciones"] > 0
    ]
    sin_calificaciones = [
        conductor
        for conductor in seed_module.CONDUCTORES
        if conductor["cantidad_calificaciones"] == 0
    ]

    assert con_calificaciones
    assert sin_calificaciones
    assert all(conductor["suma_puntajes"] > 0 for conductor in con_calificaciones)
    assert all(conductor["suma_puntajes"] == 0 for conductor in sin_calificaciones)


def test_el_seed_cubre_solicitudes_en_los_cuatro_estados(seed_module: Any) -> None:
    estados = {solicitud["estado"] for solicitud in seed_module.SOLICITUDES}

    assert estados == {"PENDIENTE", "ACEPTADO", "RECHAZADO", "VENCIDA"}


def test_el_seed_tiene_solicitudes_pendientes_vigente_y_vencida(seed_module: Any) -> None:
    pendientes = [
        solicitud for solicitud in seed_module.SOLICITUDES if solicitud["estado"] == "PENDIENTE"
    ]
    ahora = datetime.now(UTC)

    assert any(solicitud["vence_en"] > ahora for solicitud in pendientes)
    assert any(solicitud["vence_en"] < ahora for solicitud in pendientes)


def test_el_seed_tiene_un_conectado_con_vehiculo_aprobado(seed_module: Any) -> None:
    conectados = [
        conductor for conductor in seed_module.CONDUCTORES if conductor["estado"] == "CONECTADO"
    ]
    vehiculos = {vehiculo["patente"]: vehiculo for vehiculo in seed_module.VEHICULOS}
    ahora = datetime.now(UTC)

    assert conectados
    for conductor in conectados:
        patente = seed_module.VEHICULO_ACTIVO.get(conductor["dni"])
        assert patente is not None
        assert vehiculos[patente]["estado_habilitacion"] == "APROBADA"
        assert any(
            solicitud["dni_conductor"] == conductor["dni"]
            and solicitud["estado"] == "PENDIENTE"
            and solicitud["vence_en"] > ahora
            for solicitud in seed_module.SOLICITUDES
        )


def test_el_seed_tiene_documentos_de_vehiculo_vigentes_y_vencidos(
    seed_module: Any,
) -> None:
    hoy = seed_module.FECHA_BASE.date()
    vencimientos = [documento["fecha_vencimiento"] for documento in seed_module.DOCUMENTOS_VEHICULO]

    assert any(vencimiento < hoy for vencimiento in vencimientos)
    assert any(vencimiento >= hoy for vencimiento in vencimientos)


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
    assert len({s["id_viaje"] for s in seed_module.SOLICITUDES}) == len(seed_module.SOLICITUDES)
    assert len({(d["patente"], d["tipo"]) for d in seed_module.DOCUMENTOS_VEHICULO}) == len(
        seed_module.DOCUMENTOS_VEHICULO
    )


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
            assert conexion.execute(
                text("SELECT count(*) FROM vehiculo_documento")
            ).scalar_one() == len(seed_module.DOCUMENTOS_VEHICULO)
            assert conexion.execute(text("SELECT count(*) FROM solicitud")).scalar_one() == len(
                seed_module.SOLICITUDES
            )

            licencias = {
                fila[0]
                for fila in conexion.execute(
                    text(
                        """
                        SELECT fecha_vencimiento < DATE '2026-01-15'
                        FROM documento_conductor
                        WHERE tipo = 'LICENCIA'
                        """
                    )
                )
            }
            assert {False, True} <= licencias

            incoherentes = conexion.execute(
                text(
                    """
                    SELECT count(*)
                    FROM documento_conductor
                    WHERE fecha_vencimiento <= fecha_emision
                    """
                )
            ).scalar_one()
            assert incoherentes == 0

            altas_sin_motivo = conexion.execute(
                text(
                    """
                    SELECT count(*)
                    FROM (
                        SELECT motivo FROM habilitacion_evento_conductor WHERE accion = 'ALTA'
                        UNION ALL
                        SELECT motivo FROM habilitacion_evento_vehiculo WHERE accion = 'ALTA'
                    ) AS altas
                    WHERE motivo IS NULL OR length(trim(motivo)) = 0
                    """
                )
            ).scalar_one()
            assert altas_sin_motivo == 0

            disponibles = conexion.execute(
                text(
                    """
                    SELECT count(*)
                    FROM conductor
                    WHERE estado = 'DISPONIBLE'
                    """
                )
            ).scalar_one()
            assert disponibles >= 1

            estados_invalidos = conexion.execute(
                text(
                    """
                    SELECT count(*)
                    FROM conductor
                    WHERE estado NOT IN ('DESCONECTADO', 'CONECTADO', 'DISPONIBLE', 'OCUPADO')
                    """
                )
            ).scalar_one()
            assert estados_invalidos == 0

            estados_conductor = set(
                conexion.execute(text("SELECT DISTINCT estado FROM conductor")).scalars()
            )
            assert estados_conductor == {"DESCONECTADO", "CONECTADO", "DISPONIBLE", "OCUPADO"}

            sin_ubicacion = conexion.execute(
                text(
                    """
                    SELECT count(*)
                    FROM conductor
                    WHERE latitud IS NULL AND longitud IS NULL AND fecha_act_ubic IS NULL
                    """
                )
            ).scalar_one()
            sin_vehiculo_activo = conexion.execute(
                text("SELECT count(*) FROM conductor WHERE id_vehiculo_activo IS NULL")
            ).scalar_one()
            assert sin_ubicacion >= 1
            assert sin_vehiculo_activo >= 1

            con_calificaciones = conexion.execute(
                text("SELECT count(*) FROM conductor WHERE cantidad_calificaciones > 0")
            ).scalar_one()
            sin_calificaciones = conexion.execute(
                text("SELECT count(*) FROM conductor WHERE cantidad_calificaciones = 0")
            ).scalar_one()
            assert con_calificaciones >= 1
            assert sin_calificaciones >= 1

            estados_solicitud = set(
                conexion.execute(text("SELECT DISTINCT estado FROM solicitud")).scalars()
            )
            assert estados_solicitud == {"PENDIENTE", "ACEPTADO", "RECHAZADO", "VENCIDA"}

            pendientes_vigentes, pendientes_vencidas = conexion.execute(
                text(
                    """
                    SELECT
                        count(*) FILTER (WHERE vence_en > :ahora),
                        count(*) FILTER (WHERE vence_en < :ahora)
                    FROM solicitud
                    WHERE estado = 'PENDIENTE'
                    """
                ),
                {"ahora": datetime.now(UTC)},
            ).one()
            assert pendientes_vigentes >= 1
            assert pendientes_vencidas >= 1

            conectado_habilitado = conexion.execute(
                text(
                    """
                    SELECT count(*)
                    FROM conductor c
                    JOIN vehiculo v ON v.id_vehiculo = c.id_vehiculo_activo
                    JOIN solicitud s ON s.id_conductor = c.id_conductor
                    WHERE c.estado = 'CONECTADO'
                      AND v.estado_habilitacion = 'APROBADA'
                      AND s.estado = 'PENDIENTE'
                      AND s.vence_en > :ahora
                    """
                ),
                {"ahora": datetime.now(UTC)},
            ).scalar_one()
            assert conectado_habilitado >= 1

            vencimientos_vehiculo = {
                fila[0]
                for fila in conexion.execute(
                    text(
                        """
                        SELECT fecha_vencimiento < :hoy
                        FROM vehiculo_documento
                        """
                    ),
                    {"hoy": seed_module.FECHA_BASE.date()},
                )
            }
            assert {False, True} <= vencimientos_vehiculo

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
