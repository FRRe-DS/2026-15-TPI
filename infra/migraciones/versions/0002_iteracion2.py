"""Esquema de la Iteración 2 de M3.

Unifica el estado operativo del conductor en una sola columna, agrega los
datos de la Iteración 2 y crea las tablas ``solicitud`` y
``vehiculo_documento``. El downgrade reconstruye los booleanos de la
Iteración 1 a partir de ``estado``.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

ESTADOS_CONDUCTOR = "'DESCONECTADO', 'CONECTADO', 'DISPONIBLE', 'OCUPADO'"
ESTADOS_SOLICITUD = "'PENDIENTE', 'ACEPTADO', 'RECHAZADO', 'VENCIDA'"
RESPUESTAS_SOLICITUD = "'ACEPTADO', 'RECHAZADO'"
TIPOS_DOCUMENTO_VEHICULO = "'SEGURO', 'CEDULA_VERDE', 'VTV'"


def upgrade() -> None:
    # 1. estado reemplaza a conectado y disponible.
    op.add_column(
        "conductor",
        sa.Column(
            "estado",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'DESCONECTADO'"),
        ),
    )
    op.execute(
        """
        UPDATE conductor
        SET estado = CASE
            WHEN conectado IS NOT TRUE THEN 'DESCONECTADO'
            WHEN disponible IS TRUE THEN 'DISPONIBLE'
            ELSE 'CONECTADO'
        END
        """
    )
    op.create_check_constraint(
        op.f("ck_conductor_estado"),
        "conductor",
        f"estado IN ({ESTADOS_CONDUCTOR})",
    )
    op.create_index("ix_conductor_estado", "conductor", ["estado"])
    op.drop_index("ix_conductor_disponible", table_name="conductor")
    op.drop_column("conductor", "disponible")
    op.drop_column("conductor", "conectado")

    # 2. Columnas nuevas del conductor.
    op.add_column("conductor", sa.Column("id_vehiculo_activo", sa.BigInteger(), nullable=True))
    op.add_column(
        "conductor",
        sa.Column("fecha_ultimo_cambio_estado", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "conductor",
        sa.Column(
            "suma_puntajes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "conductor",
        sa.Column(
            "cantidad_calificaciones",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_foreign_key(
        op.f("fk_conductor_vehiculo_activo"),
        "conductor",
        "vehiculo",
        ["id_vehiculo_activo"],
        ["id_vehiculo"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        op.f("ck_conductor_suma_puntajes_no_negativa"),
        "conductor",
        "suma_puntajes >= 0",
    )
    op.create_check_constraint(
        op.f("ck_conductor_cantidad_calificaciones_no_negativa"),
        "conductor",
        "cantidad_calificaciones >= 0",
    )
    op.create_check_constraint(
        op.f("ck_conductor_puntajes_coherentes"),
        "conductor",
        "cantidad_calificaciones > 0 OR suma_puntajes = 0",
    )
    op.create_index("ix_conductor_id_vehiculo_activo", "conductor", ["id_vehiculo_activo"])

    # 3. Sincronizar el flag de los tipos de servicio con la habilitación del vehículo.
    op.execute(
        """
        UPDATE vehiculo_tipo_servicio AS vts
        SET habilitado = (v.estado_habilitacion = 'APROBADA')
        FROM vehiculo AS v
        WHERE vts.id_vehiculo = v.id_vehiculo
        """
    )

    # 4. Solicitudes de viaje ofrecidas al conductor.
    op.create_table(
        "solicitud",
        sa.Column("id_solicitud", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("id_conductor", sa.BigInteger(), nullable=False),
        sa.Column("id_viaje", sa.BigInteger(), nullable=True),
        sa.Column(
            "estado",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'PENDIENTE'"),
        ),
        sa.Column("vence_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("respuesta", sa.String(length=20), nullable=True),
        sa.Column("hora_rta", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "fecha_alta",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["id_conductor"],
            ["conductor.id_conductor"],
            name=op.f("fk_solicitud_conductor"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            f"estado IN ({ESTADOS_SOLICITUD})",
            name=op.f("ck_solicitud_estado"),
        ),
        sa.CheckConstraint(
            f"respuesta IS NULL OR respuesta IN ({RESPUESTAS_SOLICITUD})",
            name=op.f("ck_solicitud_respuesta"),
        ),
        sa.CheckConstraint(
            "(respuesta IS NULL AND hora_rta IS NULL) OR "
            "(respuesta IS NOT NULL AND hora_rta IS NOT NULL)",
            name=op.f("ck_solicitud_respuesta_y_hora_juntas"),
        ),
        sa.CheckConstraint(
            "respuesta IS NULL OR estado = respuesta",
            name=op.f("ck_solicitud_estado_coincide_con_respuesta"),
        ),
    )
    op.create_index(
        "ix_solicitud_id_conductor_estado",
        "solicitud",
        ["id_conductor", "estado"],
    )

    # 5. Documentación del vehículo.
    op.create_table(
        "vehiculo_documento",
        sa.Column("id_documento", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("id_vehiculo", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("numero", sa.String(length=50), nullable=False),
        sa.Column("entidad_emisora", sa.String(length=255), nullable=True),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column("url_archivo", sa.String(length=500), nullable=False),
        sa.Column(
            "fecha_registro",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["id_vehiculo"],
            ["vehiculo.id_vehiculo"],
            name=op.f("fk_vehiculo_documento_vehiculo"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            f"tipo IN ({TIPOS_DOCUMENTO_VEHICULO})",
            name=op.f("ck_vehiculo_documento_tipo"),
        ),
        sa.CheckConstraint(
            "fecha_vencimiento > fecha_emision",
            name=op.f("ck_vehiculo_documento_fechas_coherentes"),
        ),
        sa.CheckConstraint(
            "length(trim(numero)) > 0",
            name=op.f("ck_vehiculo_documento_numero_obligatorio"),
        ),
    )
    op.create_index(
        "ix_vehiculo_documento_id_vehiculo",
        "vehiculo_documento",
        ["id_vehiculo"],
    )


def downgrade() -> None:
    op.drop_index("ix_vehiculo_documento_id_vehiculo", table_name="vehiculo_documento")
    op.drop_table("vehiculo_documento")

    op.drop_index("ix_solicitud_id_conductor_estado", table_name="solicitud")
    op.drop_table("solicitud")

    op.drop_index("ix_conductor_id_vehiculo_activo", table_name="conductor")
    op.drop_constraint(op.f("ck_conductor_puntajes_coherentes"), "conductor", type_="check")
    op.drop_constraint(
        op.f("ck_conductor_cantidad_calificaciones_no_negativa"),
        "conductor",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_conductor_suma_puntajes_no_negativa"),
        "conductor",
        type_="check",
    )
    op.drop_constraint(op.f("fk_conductor_vehiculo_activo"), "conductor", type_="foreignkey")
    op.drop_column("conductor", "cantidad_calificaciones")
    op.drop_column("conductor", "suma_puntajes")
    op.drop_column("conductor", "fecha_ultimo_cambio_estado")
    op.drop_column("conductor", "id_vehiculo_activo")

    op.add_column(
        "conductor",
        sa.Column(
            "disponible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "conductor",
        sa.Column(
            "conectado",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute(
        """
        UPDATE conductor
        SET conectado = estado IN ('CONECTADO', 'DISPONIBLE', 'OCUPADO'),
            disponible = estado = 'DISPONIBLE'
        """
    )
    op.drop_index("ix_conductor_estado", table_name="conductor")
    op.drop_constraint(op.f("ck_conductor_estado"), "conductor", type_="check")
    op.drop_column("conductor", "estado")
    op.create_index("ix_conductor_disponible", "conductor", ["disponible"])
