"""Modelos SQLAlchemy del módulo M3.

El esquema mantiene una base de datos propia por servicio (RNF-05). Los
estados se guardan como texto con restricciones CHECK para que la base sea
la última línea de defensa, además de las validaciones de dominio.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    MetaData,
    String,
    UniqueConstraint,
    false,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

ESTADOS_HABILITACION = ("PENDIENTE", "OBSERVADA", "APROBADA", "SUSPENDIDA", "RECHAZADA")
TIPOS_VEHICULO = ("AUTO", "MOTO")
TIPOS_SERVICIO = ("PASAJEROS", "ENVIOS")
ACCIONES_HABILITACION = ("ALTA", "APROBAR", "OBSERVAR", "SUSPENDER", "RECHAZAR")
ESTADOS_DOCUMENTO = ("VIGENTE", "VENCIDO")
TIPOS_DOCUMENTO = ("LICENCIA", "SEGURO")

_ESTADOS_SQL = ", ".join(f"'{estado}'" for estado in ESTADOS_HABILITACION)
_TIPOS_VEHICULO_SQL = ", ".join(f"'{tipo}'" for tipo in TIPOS_VEHICULO)
_TIPOS_SERVICIO_SQL = ", ".join(f"'{tipo}'" for tipo in TIPOS_SERVICIO)
_ACCIONES_SQL = ", ".join(f"'{accion}'" for accion in ACCIONES_HABILITACION)
_ESTADOS_DOCUMENTO_SQL = ", ".join(f"'{estado}'" for estado in ESTADOS_DOCUMENTO)
_TIPOS_DOCUMENTO_SQL = ", ".join(f"'{tipo}'" for tipo in TIPOS_DOCUMENTO)

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Conductor(Base):
    __tablename__ = "conductor"
    __table_args__ = (
        UniqueConstraint("dni", name="uq_conductor_dni"),
        CheckConstraint(
            f"estado_habilitacion IN ({_ESTADOS_SQL})",
            name="estado_habilitacion",
        ),
        CheckConstraint("dni ~ '^[0-9]{7,8}$'", name="dni_formato"),
        CheckConstraint("length(trim(nombre)) > 0", name="nombre_obligatorio"),
        CheckConstraint("length(trim(apellido)) > 0", name="apellido_obligatorio"),
        CheckConstraint("length(trim(telefono)) > 0", name="telefono_obligatorio"),
        CheckConstraint(
            "email ~ '^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$'", name="email_formato"
        ),
        Index("ix_conductor_estado_habilitacion", "estado_habilitacion"),
        Index("ix_conductor_disponible", "disponible"),
    )

    id_conductor: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    dni: Mapped[str] = mapped_column(String(8), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    telefono: Mapped[str] = mapped_column(String(30), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    estado_habilitacion: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'PENDIENTE'"), default="PENDIENTE"
    )
    conectado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=false(), default=False
    )
    disponible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=false(), default=False
    )
    fecha_alta: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    documentos: Mapped[list[DocumentoConductor]] = relationship(
        back_populates="conductor",
        cascade="all, delete-orphan",
        order_by="DocumentoConductor.fecha_vencimiento",
    )
    vehiculos: Mapped[list[Vehiculo]] = relationship(
        back_populates="conductor",
        cascade="all, delete-orphan",
        order_by="Vehiculo.id_vehiculo",
    )
    eventos_habilitacion: Mapped[list[HabilitacionEventoConductor]] = relationship(
        back_populates="conductor",
        cascade="all, delete-orphan",
        order_by="HabilitacionEventoConductor.fecha",
    )


class Vehiculo(Base):
    __tablename__ = "vehiculo"
    __table_args__ = (
        UniqueConstraint("patente", name="uq_vehiculo_patente"),
        CheckConstraint(f"tipo IN ({_TIPOS_VEHICULO_SQL})", name="tipo"),
        CheckConstraint(
            f"estado_habilitacion IN ({_ESTADOS_SQL})",
            name="estado_habilitacion",
        ),
        CheckConstraint("anio >= 1900 AND anio <= 2100", name="anio_valido"),
        CheckConstraint("length(trim(marca)) > 0", name="marca_obligatoria"),
        CheckConstraint("length(trim(modelo)) > 0", name="modelo_obligatorio"),
        Index("ix_vehiculo_id_conductor", "id_conductor"),
        Index("ix_vehiculo_estado_habilitacion", "estado_habilitacion"),
    )

    id_vehiculo: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    id_conductor: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("conductor.id_conductor", ondelete="CASCADE", name="fk_vehiculo_conductor"),
        nullable=False,
    )
    patente: Mapped[str] = mapped_column(String(10), nullable=False)
    marca: Mapped[str] = mapped_column(String(80), nullable=False)
    modelo: Mapped[str] = mapped_column(String(80), nullable=False)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    estado_habilitacion: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'PENDIENTE'"), default="PENDIENTE"
    )
    fecha_alta: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    conductor: Mapped[Conductor] = relationship(back_populates="vehiculos")
    tipos_servicio: Mapped[list[VehiculoTipoServicio]] = relationship(
        back_populates="vehiculo",
        cascade="all, delete-orphan",
        order_by="VehiculoTipoServicio.tipo_servicio",
    )
    eventos_habilitacion: Mapped[list[HabilitacionEventoVehiculo]] = relationship(
        back_populates="vehiculo",
        cascade="all, delete-orphan",
        order_by="HabilitacionEventoVehiculo.fecha",
    )


class VehiculoTipoServicio(Base):
    __tablename__ = "vehiculo_tipo_servicio"
    __table_args__ = (
        UniqueConstraint(
            "id_vehiculo", "tipo_servicio", name="uq_vehiculo_tipo_servicio_vehiculo_tipo"
        ),
        CheckConstraint(f"tipo_servicio IN ({_TIPOS_SERVICIO_SQL})", name="tipo_servicio"),
        Index("ix_vehiculo_tipo_servicio_tipo", "tipo_servicio"),
    )

    id_vehiculo_tipo_servicio: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    id_vehiculo: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "vehiculo.id_vehiculo",
            ondelete="CASCADE",
            name="fk_vehiculo_tipo_servicio_vehiculo",
        ),
        nullable=False,
    )
    tipo_servicio: Mapped[str] = mapped_column(String(20), nullable=False)
    habilitado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=false(), default=False
    )

    vehiculo: Mapped[Vehiculo] = relationship(back_populates="tipos_servicio")


class DocumentoConductor(Base):
    __tablename__ = "documento_conductor"
    __table_args__ = (
        CheckConstraint(f"tipo IN ({_TIPOS_DOCUMENTO_SQL})", name="tipo"),
        CheckConstraint(f"estado IN ({_ESTADOS_DOCUMENTO_SQL})", name="estado"),
        CheckConstraint("fecha_vencimiento > fecha_emision", name="fechas_coherentes"),
        CheckConstraint("length(trim(numero)) > 0", name="numero_obligatorio"),
        Index("ix_documento_conductor_id_conductor", "id_conductor"),
    )

    id_documento: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    id_conductor: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "conductor.id_conductor",
            ondelete="CASCADE",
            name="fk_documento_conductor_conductor",
        ),
        nullable=False,
    )
    tipo: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'LICENCIA'"), default="LICENCIA"
    )
    numero: Mapped[str] = mapped_column(String(50), nullable=False)
    categoria: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fecha_emision: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_vencimiento: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    url_archivo: Mapped[str] = mapped_column(String(500), nullable=False)
    estado: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default=text("'VIGENTE'"), default="VIGENTE"
    )
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    conductor: Mapped[Conductor] = relationship(back_populates="documentos")


class HabilitacionEventoConductor(Base):
    __tablename__ = "habilitacion_evento_conductor"
    __table_args__ = (
        CheckConstraint(
            f"estado_anterior IS NULL OR estado_anterior IN ({_ESTADOS_SQL})",
            name="estado_anterior",
        ),
        CheckConstraint(f"estado_nuevo IN ({_ESTADOS_SQL})", name="estado_nuevo"),
        CheckConstraint(f"accion IN ({_ACCIONES_SQL})", name="accion"),
        CheckConstraint(
            "accion = 'ALTA' OR (motivo IS NOT NULL AND length(trim(motivo)) > 0)",
            name="motivo_requerido",
        ),
        Index("ix_habilitacion_evento_conductor_id_conductor", "id_conductor"),
    )

    id_evento: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    id_conductor: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "conductor.id_conductor",
            ondelete="CASCADE",
            name="fk_habilitacion_evento_conductor_conductor",
        ),
        nullable=False,
    )
    estado_anterior: Mapped[str | None] = mapped_column(String(20), nullable=True)
    estado_nuevo: Mapped[str] = mapped_column(String(20), nullable=False)
    accion: Mapped[str] = mapped_column(String(20), nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    id_operador: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    conductor: Mapped[Conductor] = relationship(back_populates="eventos_habilitacion")


class HabilitacionEventoVehiculo(Base):
    __tablename__ = "habilitacion_evento_vehiculo"
    __table_args__ = (
        CheckConstraint(
            f"estado_anterior IS NULL OR estado_anterior IN ({_ESTADOS_SQL})",
            name="estado_anterior",
        ),
        CheckConstraint(f"estado_nuevo IN ({_ESTADOS_SQL})", name="estado_nuevo"),
        CheckConstraint(f"accion IN ({_ACCIONES_SQL})", name="accion"),
        CheckConstraint(
            "accion = 'ALTA' OR (motivo IS NOT NULL AND length(trim(motivo)) > 0)",
            name="motivo_requerido",
        ),
        Index("ix_habilitacion_evento_vehiculo_id_vehiculo", "id_vehiculo"),
    )

    id_evento: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    id_vehiculo: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "vehiculo.id_vehiculo",
            ondelete="CASCADE",
            name="fk_habilitacion_evento_vehiculo_vehiculo",
        ),
        nullable=False,
    )
    estado_anterior: Mapped[str | None] = mapped_column(String(20), nullable=True)
    estado_nuevo: Mapped[str] = mapped_column(String(20), nullable=False)
    accion: Mapped[str] = mapped_column(String(20), nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    id_operador: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    vehiculo: Mapped[Vehiculo] = relationship(back_populates="eventos_habilitacion")
