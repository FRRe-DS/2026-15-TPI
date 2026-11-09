"""T080: esquema, unicidad, CHECK, claves foráneas y defaults de M3."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.infraestructura.db.modelos import Base
from sqlalchemy import CheckConstraint, Date, UniqueConstraint, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

TABLAS = {
    "conductor",
    "vehiculo",
    "vehiculo_tipo_servicio",
    "documento_conductor",
    "vehiculo_documento",
    "solicitud",
    "habilitacion_evento_conductor",
    "habilitacion_evento_vehiculo",
}


def _checks(tabla: str) -> str:
    return " ".join(
        str(constraint.sqltext)
        for constraint in Base.metadata.tables[tabla].constraints
        if isinstance(constraint, CheckConstraint)
    )


def test_existen_las_ocho_tablas_en_el_metadata() -> None:
    assert TABLAS <= set(Base.metadata.tables)


def test_conductor_dni_y_vehiculo_patente_son_unicos_en_el_metadata() -> None:
    uniques_conductor = {
        constraint.name
        for constraint in Base.metadata.tables["conductor"].constraints
        if isinstance(constraint, UniqueConstraint)
    }
    uniques_vehiculo = {
        constraint.name
        for constraint in Base.metadata.tables["vehiculo"].constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert "uq_conductor_dni" in uniques_conductor
    assert "uq_vehiculo_patente" in uniques_vehiculo


def test_checks_de_estados_tipos_y_acciones_en_el_metadata() -> None:
    checks_conductor = _checks("conductor")
    checks_vehiculo = _checks("vehiculo")
    checks_servicio = _checks("vehiculo_tipo_servicio")
    checks_documento_vehiculo = _checks("vehiculo_documento")
    checks_solicitud = _checks("solicitud")
    checks_evento_conductor = _checks("habilitacion_evento_conductor")
    checks_evento_vehiculo = _checks("habilitacion_evento_vehiculo")

    for estado in ("PENDIENTE", "OBSERVADA", "APROBADA", "SUSPENDIDA", "RECHAZADA"):
        assert estado in checks_conductor
        assert estado in checks_vehiculo
        assert estado in checks_evento_conductor
        assert estado in checks_evento_vehiculo

    for estado in ("DESCONECTADO", "CONECTADO", "DISPONIBLE", "OCUPADO"):
        assert estado in checks_conductor

    assert "cantidad_calificaciones = 0 OR" in checks_conductor
    assert "5 * cantidad_calificaciones" in checks_conductor

    for estado in ("PENDIENTE", "ACEPTADO", "RECHAZADO", "VENCIDA"):
        assert estado in checks_solicitud

    for respuesta in ("ACEPTADO", "RECHAZADO"):
        assert respuesta in checks_solicitud

    for tipo in ("SEGURO", "CEDULA_VERDE", "VTV"):
        assert tipo in checks_documento_vehiculo

    assert "'AUTO'" in checks_vehiculo
    assert "'MOTO'" in checks_vehiculo
    assert "'PASAJEROS'" in checks_servicio
    assert "'ENVIOS'" in checks_servicio

    for accion in ("ALTA", "APROBAR", "OBSERVAR", "SUSPENDER", "RECHAZAR"):
        assert accion in checks_evento_conductor
        assert accion in checks_evento_vehiculo


def test_documento_sin_estado_con_fechas_date_y_solo_licencia() -> None:
    documento = Base.metadata.tables["documento_conductor"]

    assert "estado" not in documento.c
    assert isinstance(documento.c.fecha_emision.type, Date)
    assert isinstance(documento.c.fecha_vencimiento.type, Date)

    checks = _checks("documento_conductor")
    assert "'LICENCIA'" in checks
    assert "'SEGURO'" not in checks
    assert "fecha_vencimiento > fecha_emision" in checks


def test_eventos_con_motivo_obligatorio_y_fk_restrict() -> None:
    for nombre in (
        "habilitacion_evento_conductor",
        "habilitacion_evento_vehiculo",
    ):
        tabla = Base.metadata.tables[nombre]
        assert tabla.c.motivo.nullable is False
        checks = _checks(nombre)
        assert "length(trim(motivo)) > 0" in checks
        assert "accion = 'ALTA'" not in checks
        assert all(fk.ondelete == "RESTRICT" for fk in tabla.foreign_keys)


def test_conductor_tiene_ubicacion_opcional() -> None:
    conductor = Base.metadata.tables["conductor"]

    for columna in ("latitud", "longitud", "fecha_act_ubic"):
        assert columna in conductor.c
        assert conductor.c[columna].nullable is True


def test_defaults_de_habilitacion_y_estado_operativo_en_el_metadata() -> None:
    conductor = Base.metadata.tables["conductor"]
    vehiculo = Base.metadata.tables["vehiculo"]
    documento_vehiculo = Base.metadata.tables["vehiculo_documento"]
    solicitud = Base.metadata.tables["solicitud"]
    tipo_servicio = Base.metadata.tables["vehiculo_tipo_servicio"]

    assert "PENDIENTE" in str(conductor.c.estado_habilitacion.server_default.arg)
    assert "PENDIENTE" in str(vehiculo.c.estado_habilitacion.server_default.arg)
    assert "DESCONECTADO" in str(conductor.c.estado.server_default.arg)
    assert str(conductor.c.suma_puntajes.server_default.arg) == "0"
    assert str(conductor.c.cantidad_calificaciones.server_default.arg) == "0"
    assert "PENDIENTE" in str(solicitud.c.estado.server_default.arg)
    assert str(tipo_servicio.c.habilitado.server_default.arg).lower() == "false"
    assert "estado" not in documento_vehiculo.c


def test_conductor_tiene_vehiculo_activo_y_totales_de_puntaje() -> None:
    conductor = Base.metadata.tables["conductor"]

    assert conductor.c.id_vehiculo_activo.nullable is True
    assert conductor.c.fecha_ultimo_cambio_estado.nullable is True
    assert conductor.c.suma_puntajes.nullable is False
    assert conductor.c.cantidad_calificaciones.nullable is False


def test_solicitud_y_documento_de_vehiculo_tienen_sus_columnas() -> None:
    solicitud = Base.metadata.tables["solicitud"]
    documento_vehiculo = Base.metadata.tables["vehiculo_documento"]

    for columna in ("id_conductor", "id_viaje", "estado", "vence_en", "respuesta", "hora_rta"):
        assert columna in solicitud.c
    for columna in (
        "id_vehiculo",
        "tipo",
        "numero",
        "entidad_emisora",
        "fecha_emision",
        "fecha_vencimiento",
        "url_archivo",
        "fecha_registro",
    ):
        assert columna in documento_vehiculo.c


def test_claves_foraneas_en_el_metadata() -> None:
    esperadas = {
        ("conductor", "id_vehiculo_activo", "vehiculo", "id_vehiculo"),
        ("vehiculo", "id_conductor", "conductor", "id_conductor"),
        (
            "vehiculo_tipo_servicio",
            "id_vehiculo",
            "vehiculo",
            "id_vehiculo",
        ),
        (
            "vehiculo_documento",
            "id_vehiculo",
            "vehiculo",
            "id_vehiculo",
        ),
        (
            "solicitud",
            "id_conductor",
            "conductor",
            "id_conductor",
        ),
        (
            "documento_conductor",
            "id_conductor",
            "conductor",
            "id_conductor",
        ),
        (
            "habilitacion_evento_conductor",
            "id_conductor",
            "conductor",
            "id_conductor",
        ),
        (
            "habilitacion_evento_vehiculo",
            "id_vehiculo",
            "vehiculo",
            "id_vehiculo",
        ),
    }
    encontradas = set()
    for tabla in Base.metadata.tables.values():
        for fk in tabla.foreign_keys:
            encontradas.add((tabla.name, fk.parent.name, fk.column.table.name, fk.column.name))

    assert esperadas <= encontradas


@pytest.fixture
def motor(m3_migrada: str) -> Iterator[Engine]:
    engine = create_engine(m3_migrada)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.mark.integration
def test_postgres_contiene_todas_las_tablas(m3_migrada: str) -> None:
    from sqlalchemy import inspect

    engine = create_engine(m3_migrada)
    try:
        tablas = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert TABLAS <= tablas
    assert "alembic_version" in tablas


@pytest.mark.integration
def test_postgres_documento_sin_estado_y_eventos_restrict(m3_migrada: str) -> None:
    from sqlalchemy import inspect

    engine = create_engine(m3_migrada)
    try:
        inspector = inspect(engine)
        documento = {
            columna["name"]: columna for columna in inspector.get_columns("documento_conductor")
        }
        assert "estado" not in documento
        assert isinstance(documento["fecha_emision"]["type"], Date)
        assert isinstance(documento["fecha_vencimiento"]["type"], Date)

        for tabla in ("habilitacion_evento_conductor", "habilitacion_evento_vehiculo"):
            motivo = next(
                columna for columna in inspector.get_columns(tabla) if columna["name"] == "motivo"
            )
            assert motivo["nullable"] is False
            claves = inspector.get_foreign_keys(tabla)
            assert all(clave["options"].get("ondelete") == "RESTRICT" for clave in claves)
    finally:
        engine.dispose()


@pytest.mark.integration
def test_postgres_tiene_unicidad_y_checks(m3_migrada: str) -> None:
    engine = create_engine(m3_migrada)
    try:
        with engine.connect() as conexion:
            uniques = {
                fila[0]
                for fila in conexion.execute(
                    text(
                        """
                        SELECT conname
                        FROM pg_constraint
                        WHERE conrelid IN ('conductor'::regclass, 'vehiculo'::regclass)
                          AND contype = 'u'
                        """
                    )
                )
            }
            checks = {
                fila[0]: fila[1]
                for fila in conexion.execute(
                    text(
                        """
                        SELECT conname, pg_get_constraintdef(oid)
                        FROM pg_constraint
                        WHERE conrelid IN (
                            'conductor'::regclass,
                            'vehiculo'::regclass,
                            'vehiculo_tipo_servicio'::regclass,
                            'vehiculo_documento'::regclass,
                            'solicitud'::regclass,
                            'habilitacion_evento_conductor'::regclass,
                            'habilitacion_evento_vehiculo'::regclass
                        )
                          AND contype = 'c'
                        """
                    )
                )
            }
    finally:
        engine.dispose()

    assert {"uq_conductor_dni", "uq_vehiculo_patente"} <= uniques
    for clave in (
        "ck_conductor_estado_habilitacion",
        "ck_conductor_estado",
        "ck_conductor_suma_puntajes_no_negativa",
        "ck_conductor_cantidad_calificaciones_no_negativa",
        "ck_conductor_puntajes_coherentes",
        "ck_conductor_promedio_puntajes_rango",
        "ck_vehiculo_tipo",
        "ck_vehiculo_estado_habilitacion",
        "ck_vehiculo_tipo_servicio_tipo_servicio",
        "ck_vehiculo_documento_tipo",
        "ck_vehiculo_documento_fechas_coherentes",
        "ck_solicitud_estado",
        "ck_solicitud_respuesta",
        "ck_solicitud_respuesta_y_hora_juntas",
        "ck_solicitud_estado_coincide_con_respuesta",
        "ck_solicitud_respuesta_obligatoria",
        "ck_habilitacion_evento_conductor_accion",
        "ck_habilitacion_evento_vehiculo_accion",
    ):
        assert clave in checks
    definiciones = " ".join(checks.values())
    for valor in (
        "PENDIENTE",
        "OBSERVADA",
        "APROBADA",
        "SUSPENDIDA",
        "RECHAZADA",
        "DESCONECTADO",
        "CONECTADO",
        "DISPONIBLE",
        "OCUPADO",
        "AUTO",
        "MOTO",
        "PASAJEROS",
        "ENVIOS",
        "SEGURO",
        "CEDULA_VERDE",
        "VTV",
        "ACEPTADO",
        "RECHAZADO",
        "VENCIDA",
        "ALTA",
        "APROBAR",
        "OBSERVAR",
        "SUSPENDER",
        "RECHAZAR",
    ):
        assert valor in definiciones


@pytest.mark.integration
def test_defaults_reales_pendiente_desconectado_y_totales_en_cero(motor: Engine) -> None:
    with motor.begin() as conexion:
        conexion.execute(
            text(
                """
                INSERT INTO conductor (dni, nombre, apellido, telefono, email)
                VALUES ('20000001', 'Default', 'Prueba', '3624000099', 'default@m3.local')
                """
            )
        )
        estado_habilitacion, estado, suma, cantidad = conexion.execute(
            text(
                """
                SELECT estado_habilitacion, estado, suma_puntajes, cantidad_calificaciones
                FROM conductor WHERE dni = '20000001'
                """
            )
        ).one()

    assert (estado_habilitacion, estado) == ("PENDIENTE", "DESCONECTADO")
    assert (suma, cantidad) == (0, 0)


@pytest.mark.integration
def test_la_base_rechaza_dni_duplicado(motor: Engine) -> None:
    with motor.begin() as conexion:
        conexion.execute(
            text(
                """
                INSERT INTO conductor (dni, nombre, apellido, telefono, email)
                VALUES ('20000002', 'Uno', 'Prueba', '3624000098', 'uno@m3.local')
                """
            )
        )

    with pytest.raises(IntegrityError):
        with motor.begin() as conexion:
            conexion.execute(
                text(
                    """
                    INSERT INTO conductor (dni, nombre, apellido, telefono, email)
                    VALUES ('20000002', 'Dos', 'Prueba', '3624000097', 'dos@m3.local')
                    """
                )
            )


@pytest.mark.integration
def test_la_base_rechaza_estado_de_habilitacion_invalido(motor: Engine) -> None:
    with pytest.raises(IntegrityError):
        with motor.begin() as conexion:
            conexion.execute(
                text(
                    """
                    INSERT INTO conductor
                        (dni, nombre, apellido, telefono, email, estado_habilitacion)
                    VALUES
                        ('20000003', 'Estado', 'Invalido', '3624000096',
                         'estado@m3.local', 'EN_REVISION')
                    """
                )
            )


@pytest.mark.integration
def test_la_base_rechaza_estado_operativo_invalido(motor: Engine) -> None:
    with pytest.raises(IntegrityError):
        with motor.begin() as conexion:
            conexion.execute(
                text(
                    """
                    INSERT INTO conductor
                        (dni, nombre, apellido, telefono, email, estado)
                    VALUES
                        ('20000005', 'Estado', 'Invalido', '3624000094',
                         'operativo@m3.local', 'EN_VIAJE')
                    """
                )
            )


@pytest.mark.integration
def test_la_base_rechaza_solicitud_con_respuesta_sin_hora(motor: Engine) -> None:
    with motor.begin() as conexion:
        id_conductor = conexion.execute(
            text(
                """
                INSERT INTO conductor (dni, nombre, apellido, telefono, email)
                VALUES ('20000006', 'Soli', 'Citante', '3624000093', 'solicitud@m3.local')
                RETURNING id_conductor
                """
            )
        ).scalar_one()

    with pytest.raises(IntegrityError):
        with motor.begin() as conexion:
            conexion.execute(
                text(
                    """
                    INSERT INTO solicitud
                        (id_conductor, id_viaje, estado, vence_en, respuesta)
                    VALUES
                        (:id_conductor, 1, 'ACEPTADO', now(), 'ACEPTADO')
                    """
                ),
                {"id_conductor": id_conductor},
            )


@pytest.mark.integration
def test_la_base_rechaza_solicitud_aceptada_sin_respuesta(motor: Engine) -> None:
    with motor.begin() as conexion:
        id_conductor = conexion.execute(
            text(
                """
                INSERT INTO conductor (dni, nombre, apellido, telefono, email)
                VALUES ('20000007', 'Soli', 'Sin', '3624000092', 'sinrespuesta@m3.local')
                RETURNING id_conductor
                """
            )
        ).scalar_one()

    with pytest.raises(IntegrityError):
        with motor.begin() as conexion:
            conexion.execute(
                text(
                    """
                    INSERT INTO solicitud
                        (id_conductor, id_viaje, estado, vence_en)
                    VALUES
                        (:id_conductor, 2, 'ACEPTADO', now())
                    """
                ),
                {"id_conductor": id_conductor},
            )


@pytest.mark.integration
@pytest.mark.parametrize(
    ("dni", "suma", "cantidad"),
    [
        ("20000031", 0, 1),
        ("20000032", 6, 1),
        ("20000033", 11, 2),
    ],
)
def test_la_base_rechaza_promedio_de_puntajes_fuera_de_rango(
    motor: Engine, dni: str, suma: int, cantidad: int
) -> None:
    with pytest.raises(IntegrityError):
        with motor.begin() as conexion:
            conexion.execute(
                text(
                    """
                    INSERT INTO conductor
                        (dni, nombre, apellido, telefono, email,
                         suma_puntajes, cantidad_calificaciones)
                    VALUES
                        (:dni, 'Promedio', 'Invalido', '3624000091',
                         'promedio@m3.local', :suma, :cantidad)
                    """
                ),
                {"dni": dni, "suma": suma, "cantidad": cantidad},
            )


@pytest.mark.integration
@pytest.mark.parametrize(
    ("dni", "suma", "cantidad"),
    [
        ("20000034", 0, 0),
        ("20000035", 1, 1),
        ("20000036", 5, 1),
        ("20000037", 10, 2),
        ("20000038", 14, 3),
    ],
)
def test_la_base_acepta_promedio_de_puntajes_entre_uno_y_cinco(
    motor: Engine, dni: str, suma: int, cantidad: int
) -> None:
    with motor.begin() as conexion:
        conexion.execute(
            text(
                """
                INSERT INTO conductor
                    (dni, nombre, apellido, telefono, email,
                     suma_puntajes, cantidad_calificaciones)
                VALUES
                    (:dni, 'Promedio', 'Valido', '3624000090',
                     'promedio.valido@m3.local', :suma, :cantidad)
                """
            ),
            {"dni": dni, "suma": suma, "cantidad": cantidad},
        )


@pytest.mark.integration
def test_la_base_rechaza_tipo_de_vehiculo_invalido(motor: Engine) -> None:
    with motor.begin() as conexion:
        id_conductor = conexion.execute(
            text(
                """
                INSERT INTO conductor (dni, nombre, apellido, telefono, email)
                VALUES ('20000004', 'Tipo', 'Invalido', '3624000095', 'tipo@m3.local')
                RETURNING id_conductor
                """
            )
        ).scalar_one()

    with pytest.raises(IntegrityError):
        with motor.begin() as conexion:
            conexion.execute(
                text(
                    """
                    INSERT INTO vehiculo
                        (id_conductor, patente, marca, modelo, anio, tipo)
                    VALUES
                        (:id_conductor, 'ZZ999ZZ', 'Marca', 'Modelo', 2020, 'CAMION')
                    """
                ),
                {"id_conductor": id_conductor},
            )
