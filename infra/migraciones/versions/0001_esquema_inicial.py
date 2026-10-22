"""Esquema inicial de M3.

Crea las seis tablas del módulo, sus claves foráneas, unicidad y CHECK de
estados, tipos y acciones. El downgrade elimina todo en orden inverso.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

ESTADOS = "'PENDIENTE', 'OBSERVADA', 'APROBADA', 'SUSPENDIDA', 'RECHAZADA'"
TIPOS_VEHICULO = "'AUTO', 'MOTO'"
TIPOS_SERVICIO = "'PASAJEROS', 'ENVIOS'"
ACCIONES = "'ALTA', 'APROBAR', 'OBSERVAR', 'SUSPENDER', 'RECHAZAR'"


def upgrade() -> None:
    op.create_table(
        "conductor",
        sa.Column("id_conductor", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("dni", sa.String(length=8), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("apellido", sa.String(length=100), nullable=False),
        sa.Column("telefono", sa.String(length=30), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "estado_habilitacion",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'PENDIENTE'"),
        ),
        sa.Column("conectado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("disponible", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "fecha_alta",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("dni", name="uq_conductor_dni"),
        sa.CheckConstraint(
            f"estado_habilitacion IN ({ESTADOS})",
            name="estado_habilitacion",
        ),
        sa.CheckConstraint("dni ~ '^[0-9]{7,8}$'", name="dni_formato"),
        sa.CheckConstraint("length(trim(nombre)) > 0", name="nombre_obligatorio"),
        sa.CheckConstraint("length(trim(apellido)) > 0", name="apellido_obligatorio"),
        sa.CheckConstraint("length(trim(telefono)) > 0", name="telefono_obligatorio"),
        sa.CheckConstraint(
            "email ~ '^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$'",
            name="email_formato",
        ),
    )
    op.create_index("ix_conductor_estado_habilitacion", "conductor", ["estado_habilitacion"])
    op.create_index("ix_conductor_disponible", "conductor", ["disponible"])

    op.create_table(
        "vehiculo",
        sa.Column("id_vehiculo", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("id_conductor", sa.BigInteger(), nullable=False),
        sa.Column("patente", sa.String(length=10), nullable=False),
        sa.Column("marca", sa.String(length=80), nullable=False),
        sa.Column("modelo", sa.String(length=80), nullable=False),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column(
            "estado_habilitacion",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'PENDIENTE'"),
        ),
        sa.Column(
            "fecha_alta",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["id_conductor"],
            ["conductor.id_conductor"],
            name="fk_vehiculo_conductor",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("patente", name="uq_vehiculo_patente"),
        sa.CheckConstraint(f"tipo IN ({TIPOS_VEHICULO})", name="tipo"),
        sa.CheckConstraint(
            f"estado_habilitacion IN ({ESTADOS})",
            name="estado_habilitacion",
        ),
        sa.CheckConstraint("anio >= 1900 AND anio <= 2100", name="anio_valido"),
        sa.CheckConstraint("length(trim(marca)) > 0", name="marca_obligatoria"),
        sa.CheckConstraint("length(trim(modelo)) > 0", name="modelo_obligatorio"),
    )
    op.create_index("ix_vehiculo_id_conductor", "vehiculo", ["id_conductor"])
    op.create_index("ix_vehiculo_estado_habilitacion", "vehiculo", ["estado_habilitacion"])

    op.create_table(
        "documento_conductor",
        sa.Column("id_documento", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("id_conductor", sa.BigInteger(), nullable=False),
        sa.Column(
            "tipo",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'LICENCIA'"),
        ),
        sa.Column("numero", sa.String(length=50), nullable=False),
        sa.Column("categoria", sa.String(length=10), nullable=True),
        sa.Column("fecha_emision", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_vencimiento", sa.DateTime(timezone=True), nullable=False),
        sa.Column("url_archivo", sa.String(length=500), nullable=False),
        sa.Column(
            "estado",
            sa.String(length=10),
            nullable=False,
            server_default=sa.text("'VIGENTE'"),
        ),
        sa.Column(
            "fecha_registro",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["id_conductor"],
            ["conductor.id_conductor"],
            name="fk_documento_conductor_conductor",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("tipo IN ('LICENCIA', 'SEGURO')", name="tipo"),
        sa.CheckConstraint("estado IN ('VIGENTE', 'VENCIDO')", name="estado"),
        sa.CheckConstraint(
            "fecha_vencimiento > fecha_emision",
            name="fechas_coherentes",
        ),
        sa.CheckConstraint(
            "length(trim(numero)) > 0",
            name="numero_obligatorio",
        ),
    )
    op.create_index("ix_documento_conductor_id_conductor", "documento_conductor", ["id_conductor"])

    op.create_table(
        "habilitacion_evento_conductor",
        sa.Column("id_evento", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("id_conductor", sa.BigInteger(), nullable=False),
        sa.Column("estado_anterior", sa.String(length=20), nullable=True),
        sa.Column("estado_nuevo", sa.String(length=20), nullable=False),
        sa.Column("accion", sa.String(length=20), nullable=False),
        sa.Column("motivo", sa.String(length=500), nullable=True),
        sa.Column("id_operador", sa.BigInteger(), nullable=True),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["id_conductor"],
            ["conductor.id_conductor"],
            name="fk_habilitacion_evento_conductor_conductor",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            f"estado_anterior IS NULL OR estado_anterior IN ({ESTADOS})",
            name="estado_anterior",
        ),
        sa.CheckConstraint(
            f"estado_nuevo IN ({ESTADOS})",
            name="estado_nuevo",
        ),
        sa.CheckConstraint(
            f"accion IN ({ACCIONES})",
            name="accion",
        ),
        sa.CheckConstraint(
            "accion = 'ALTA' OR (motivo IS NOT NULL AND length(trim(motivo)) > 0)",
            name="motivo_requerido",
        ),
    )
    op.create_index(
        "ix_habilitacion_evento_conductor_id_conductor",
        "habilitacion_evento_conductor",
        ["id_conductor"],
    )

    op.create_table(
        "vehiculo_tipo_servicio",
        sa.Column(
            "id_vehiculo_tipo_servicio",
            sa.BigInteger(),
            sa.Identity(),
            primary_key=True,
        ),
        sa.Column("id_vehiculo", sa.BigInteger(), nullable=False),
        sa.Column("tipo_servicio", sa.String(length=20), nullable=False),
        sa.Column("habilitado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(
            ["id_vehiculo"],
            ["vehiculo.id_vehiculo"],
            name="fk_vehiculo_tipo_servicio_vehiculo",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "id_vehiculo",
            "tipo_servicio",
            name="uq_vehiculo_tipo_servicio_vehiculo_tipo",
        ),
        sa.CheckConstraint(
            f"tipo_servicio IN ({TIPOS_SERVICIO})",
            name="tipo_servicio",
        ),
    )
    op.create_index("ix_vehiculo_tipo_servicio_tipo", "vehiculo_tipo_servicio", ["tipo_servicio"])

    op.create_table(
        "habilitacion_evento_vehiculo",
        sa.Column("id_evento", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("id_vehiculo", sa.BigInteger(), nullable=False),
        sa.Column("estado_anterior", sa.String(length=20), nullable=True),
        sa.Column("estado_nuevo", sa.String(length=20), nullable=False),
        sa.Column("accion", sa.String(length=20), nullable=False),
        sa.Column("motivo", sa.String(length=500), nullable=True),
        sa.Column("id_operador", sa.BigInteger(), nullable=True),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["id_vehiculo"],
            ["vehiculo.id_vehiculo"],
            name="fk_habilitacion_evento_vehiculo_vehiculo",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            f"estado_anterior IS NULL OR estado_anterior IN ({ESTADOS})",
            name="estado_anterior",
        ),
        sa.CheckConstraint(
            f"estado_nuevo IN ({ESTADOS})",
            name="estado_nuevo",
        ),
        sa.CheckConstraint(
            f"accion IN ({ACCIONES})",
            name="accion",
        ),
        sa.CheckConstraint(
            "accion = 'ALTA' OR (motivo IS NOT NULL AND length(trim(motivo)) > 0)",
            name="motivo_requerido",
        ),
    )
    op.create_index(
        "ix_habilitacion_evento_vehiculo_id_vehiculo",
        "habilitacion_evento_vehiculo",
        ["id_vehiculo"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_habilitacion_evento_vehiculo_id_vehiculo",
        table_name="habilitacion_evento_vehiculo",
    )
    op.drop_table("habilitacion_evento_vehiculo")
    op.drop_index("ix_vehiculo_tipo_servicio_tipo", table_name="vehiculo_tipo_servicio")
    op.drop_table("vehiculo_tipo_servicio")
    op.drop_index(
        "ix_habilitacion_evento_conductor_id_conductor",
        table_name="habilitacion_evento_conductor",
    )
    op.drop_table("habilitacion_evento_conductor")
    op.drop_index("ix_documento_conductor_id_conductor", table_name="documento_conductor")
    op.drop_table("documento_conductor")
    op.drop_index("ix_vehiculo_estado_habilitacion", table_name="vehiculo")
    op.drop_index("ix_vehiculo_id_conductor", table_name="vehiculo")
    op.drop_table("vehiculo")
    op.drop_index("ix_conductor_disponible", table_name="conductor")
    op.drop_index("ix_conductor_estado_habilitacion", table_name="conductor")
    op.drop_table("conductor")
