"""Ids UUID (contrato 2.0.0).

Pasa las claves primarias y foráneas de ``BIGINT`` a ``UUID`` y agrega el
valor por defecto ``gen_random_uuid()`` (PostgreSQL 17, sin extensiones). Los
ids existentes se convierten de forma determinista (``md5`` del entero con un
prefijo por entidad), así que las filas y sus relaciones se conservan.

Las tablas de eventos de habilitación ganan ``secuencia``, un contador interno
que conserva el orden de registro del historial (un UUID no tiene orden).

El downgrade no puede recuperar los enteros originales: vacía las tablas de M3
antes de volver a ``BIGINT`` con identidad.
"""

from __future__ import annotations

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

# (tabla, columna, prefijo del UUID derivado)
CLAVES_PRIMARIAS = (
    ("conductor", "id_conductor", "conductor"),
    ("vehiculo", "id_vehiculo", "vehiculo"),
    ("vehiculo_tipo_servicio", "id_vehiculo_tipo_servicio", "vehiculo_tipo_servicio"),
    ("documento_conductor", "id_documento", "documento_conductor"),
    ("vehiculo_documento", "id_documento", "vehiculo_documento"),
    ("solicitud", "id_solicitud", "solicitud"),
    ("habilitacion_evento_conductor", "id_evento", "habilitacion_evento_conductor"),
    ("habilitacion_evento_vehiculo", "id_evento", "habilitacion_evento_vehiculo"),
)

# (tabla, columna, columna referenciada, tabla referenciada, prefijo, nombre, ondelete)
CLAVES_FORANEAS = (
    ("vehiculo", "id_conductor", "id_conductor", "conductor", "fk_vehiculo_conductor", "CASCADE"),
    (
        "conductor",
        "id_vehiculo_activo",
        "id_vehiculo",
        "vehiculo",
        "fk_conductor_vehiculo_activo",
        "SET NULL",
    ),
    (
        "documento_conductor",
        "id_conductor",
        "id_conductor",
        "conductor",
        "fk_documento_conductor_conductor",
        "CASCADE",
    ),
    (
        "habilitacion_evento_conductor",
        "id_conductor",
        "id_conductor",
        "conductor",
        "fk_habilitacion_evento_conductor_conductor",
        "RESTRICT",
    ),
    (
        "habilitacion_evento_vehiculo",
        "id_vehiculo",
        "id_vehiculo",
        "vehiculo",
        "fk_habilitacion_evento_vehiculo_vehiculo",
        "RESTRICT",
    ),
    (
        "vehiculo_tipo_servicio",
        "id_vehiculo",
        "id_vehiculo",
        "vehiculo",
        "fk_vehiculo_tipo_servicio_vehiculo",
        "CASCADE",
    ),
    (
        "solicitud",
        "id_conductor",
        "id_conductor",
        "conductor",
        "fk_solicitud_conductor",
        "RESTRICT",
    ),
    (
        "vehiculo_documento",
        "id_vehiculo",
        "id_vehiculo",
        "vehiculo",
        "fk_vehiculo_documento_vehiculo",
        "RESTRICT",
    ),
)

TABLAS_DE_EVENTOS = (
    "habilitacion_evento_conductor",
    "habilitacion_evento_vehiculo",
)

# Columnas sin clave foránea que también pasan a UUID: (tabla, columna, prefijo)
REFERENCIAS_EXTERNAS = (
    ("habilitacion_evento_conductor", "id_operador", "operador"),
    ("habilitacion_evento_vehiculo", "id_operador", "operador"),
    ("solicitud", "id_viaje", "viaje"),
)

# Prefijo del UUID derivado de cada columna foránea, igual al de la clave que referencia.
PREFIJO_DE_TABLA = {tabla: prefijo for tabla, columna, prefijo in CLAVES_PRIMARIAS}


def _uuid_derivado(columna: str, prefijo: str) -> str:
    return f"md5('{prefijo}:' || {columna}::text)::uuid"


def _soltar_claves_foraneas() -> None:
    for tabla, _columna, _destino, _tabla_destino, nombre, _ondelete in CLAVES_FORANEAS:
        op.execute(f"ALTER TABLE {tabla} DROP CONSTRAINT {nombre}")


def _crear_claves_foraneas() -> None:
    for tabla, columna, destino, tabla_destino, nombre, ondelete in CLAVES_FORANEAS:
        op.execute(
            f"ALTER TABLE {tabla} ADD CONSTRAINT {nombre} "
            f"FOREIGN KEY ({columna}) REFERENCES {tabla_destino} ({destino}) "
            f"ON DELETE {ondelete}"
        )


def _agregar_secuencia() -> None:
    """Agrega ``secuencia`` ordenada por el id entero anterior y la deja como identidad."""
    for tabla in TABLAS_DE_EVENTOS:
        op.execute(f"ALTER TABLE {tabla} ADD COLUMN secuencia bigint")
        op.execute(
            f"UPDATE {tabla} AS t SET secuencia = s.orden FROM ("
            f"SELECT id_evento, row_number() OVER (ORDER BY id_evento) AS orden FROM {tabla}"
            ") AS s WHERE t.id_evento = s.id_evento"
        )
        op.execute(f"ALTER TABLE {tabla} ALTER COLUMN secuencia SET NOT NULL")
        op.execute(f"ALTER TABLE {tabla} ALTER COLUMN secuencia ADD GENERATED ALWAYS AS IDENTITY")
        op.execute(
            f"SELECT setval(pg_get_serial_sequence('{tabla}', 'secuencia'), "
            f"coalesce((SELECT max(secuencia) FROM {tabla}), 0) + 1, false)"
        )


def upgrade() -> None:
    _agregar_secuencia()
    _soltar_claves_foraneas()

    for tabla, columna, prefijo in CLAVES_PRIMARIAS:
        op.execute(f"ALTER TABLE {tabla} ALTER COLUMN {columna} DROP IDENTITY IF EXISTS")
        op.execute(
            f"ALTER TABLE {tabla} ALTER COLUMN {columna} "
            f"TYPE uuid USING {_uuid_derivado(columna, prefijo)}"
        )
        op.execute(f"ALTER TABLE {tabla} ALTER COLUMN {columna} SET DEFAULT gen_random_uuid()")

    for tabla, columna, _destino, tabla_destino, _nombre, _ondelete in CLAVES_FORANEAS:
        prefijo = PREFIJO_DE_TABLA[tabla_destino]
        op.execute(
            f"ALTER TABLE {tabla} ALTER COLUMN {columna} "
            f"TYPE uuid USING {_uuid_derivado(columna, prefijo)}"
        )

    for tabla, columna, prefijo in REFERENCIAS_EXTERNAS:
        op.execute(
            f"ALTER TABLE {tabla} ALTER COLUMN {columna} "
            f"TYPE uuid USING {_uuid_derivado(columna, prefijo)}"
        )

    _crear_claves_foraneas()


def downgrade() -> None:
    tablas = ", ".join(tabla for tabla, _columna, _prefijo in CLAVES_PRIMARIAS)
    op.execute(f"TRUNCATE TABLE {tablas} CASCADE")
    for tabla in TABLAS_DE_EVENTOS:
        op.execute(f"ALTER TABLE {tabla} DROP COLUMN secuencia")
    _soltar_claves_foraneas()

    for tabla, columna, _prefijo in CLAVES_PRIMARIAS:
        op.execute(f"ALTER TABLE {tabla} ALTER COLUMN {columna} DROP DEFAULT")
        op.execute(f"ALTER TABLE {tabla} ALTER COLUMN {columna} TYPE bigint USING 0")
        op.execute(
            f"ALTER TABLE {tabla} ALTER COLUMN {columna} ADD GENERATED BY DEFAULT AS IDENTITY"
        )

    for tabla, columna, *_ in CLAVES_FORANEAS:
        op.execute(f"ALTER TABLE {tabla} ALTER COLUMN {columna} TYPE bigint USING 0")

    for tabla, columna, _prefijo in REFERENCIAS_EXTERNAS:
        op.execute(f"ALTER TABLE {tabla} ALTER COLUMN {columna} TYPE bigint USING 0")

    _crear_claves_foraneas()
