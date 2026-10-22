"""Carga determinista e idempotente de datos de demostración de M3.

El script puede ejecutarse todas las veces que sea necesario: identifica cada
registro por su clave natural (DNI, patente, número de licencia, tipo de
servicio o evento) y sólo inserta lo que falta.

Uso:
    DATABASE_URL=postgresql+psycopg://... python infra/seed/cargar_datos.py
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

# Permite ejecutar el script directamente desde el repositorio.
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.infraestructura.db.modelos import (  # noqa: E402
    Conductor,
    DocumentoConductor,
    HabilitacionEventoConductor,
    HabilitacionEventoVehiculo,
    Vehiculo,
    VehiculoTipoServicio,
)
from app.infraestructura.db.sesion import crear_engine, crear_sessionmaker  # noqa: E402

FECHA_BASE = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
FECHA_EMISION = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
FECHA_VIGENTE = datetime(2035, 12, 31, 0, 0, tzinfo=UTC)
FECHA_VENCIDA = datetime(2020, 12, 31, 0, 0, tzinfo=UTC)
ID_OPERADOR_SEED = 101

CONDUCTORES: tuple[dict[str, Any], ...] = (
    {
        "dni": "30111222",
        "nombre": "Ana",
        "apellido": "Pérez",
        "telefono": "+5493624000001",
        "email": "ana.perez@m3.local",
        "estado_habilitacion": "APROBADA",
        "conectado": True,
        "disponible": True,
    },
    {
        "dni": "28444555",
        "nombre": "Bruno",
        "apellido": "Gómez",
        "telefono": "+5493624000002",
        "email": "bruno.gomez@m3.local",
        "estado_habilitacion": "OBSERVADA",
        "conectado": False,
        "disponible": False,
    },
    {
        "dni": "35777888",
        "nombre": "Carla",
        "apellido": "Díaz",
        "telefono": "+5493624000003",
        "email": "carla.diaz@m3.local",
        "estado_habilitacion": "PENDIENTE",
        "conectado": False,
        "disponible": False,
    },
)

VEHICULOS: tuple[dict[str, Any], ...] = (
    {
        "dni_conductor": "30111222",
        "patente": "AB123CD",
        "marca": "Toyota",
        "modelo": "Corolla",
        "anio": 2022,
        "tipo": "AUTO",
        "estado_habilitacion": "APROBADA",
        "tipos_servicio": (("PASAJEROS", True), ("ENVIOS", True)),
    },
    {
        "dni_conductor": "28444555",
        "patente": "MOTO77",
        "marca": "Honda",
        "modelo": "CB 190",
        "anio": 2021,
        "tipo": "MOTO",
        "estado_habilitacion": "PENDIENTE",
        "tipos_servicio": (("PASAJEROS", False),),
    },
    {
        "dni_conductor": "35777888",
        "patente": "AC456EF",
        "marca": "Fiat",
        "modelo": "Cronos",
        "anio": 2023,
        "tipo": "AUTO",
        "estado_habilitacion": "PENDIENTE",
        "tipos_servicio": (("PASAJEROS", False), ("ENVIOS", False)),
    },
)

DOCUMENTOS: tuple[dict[str, Any], ...] = (
    {
        "dni_conductor": "30111222",
        "numero": "LIC-30111222",
        "categoria": "B1",
        "fecha_emision": FECHA_EMISION,
        "fecha_vencimiento": FECHA_VIGENTE,
        "estado": "VIGENTE",
        "url_archivo": "https://documentos.m3.local/licencias/30111222.pdf",
    },
    {
        "dni_conductor": "28444555",
        "numero": "LIC-28444555",
        "categoria": "A2",
        "fecha_emision": FECHA_EMISION,
        "fecha_vencimiento": FECHA_VENCIDA,
        "estado": "VENCIDO",
        "url_archivo": "https://documentos.m3.local/licencias/28444555.pdf",
    },
    {
        "dni_conductor": "35777888",
        "numero": "LIC-35777888",
        "categoria": "B1",
        "fecha_emision": FECHA_EMISION,
        "fecha_vencimiento": FECHA_VIGENTE,
        "estado": "VIGENTE",
        "url_archivo": "https://documentos.m3.local/licencias/35777888.pdf",
    },
)

EVENTOS_CONDUCTOR: tuple[dict[str, Any], ...] = (
    {
        "dni_conductor": "30111222",
        "estado_anterior": None,
        "estado_nuevo": "PENDIENTE",
        "accion": "ALTA",
        "motivo": None,
        "id_operador": None,
    },
    {
        "dni_conductor": "30111222",
        "estado_anterior": "PENDIENTE",
        "estado_nuevo": "APROBADA",
        "accion": "APROBAR",
        "motivo": "Documentación completa y licencia vigente.",
        "id_operador": ID_OPERADOR_SEED,
    },
    {
        "dni_conductor": "28444555",
        "estado_anterior": None,
        "estado_nuevo": "PENDIENTE",
        "accion": "ALTA",
        "motivo": None,
        "id_operador": None,
    },
    {
        "dni_conductor": "28444555",
        "estado_anterior": "PENDIENTE",
        "estado_nuevo": "OBSERVADA",
        "accion": "OBSERVAR",
        "motivo": "Licencia de conducir vencida.",
        "id_operador": ID_OPERADOR_SEED,
    },
    {
        "dni_conductor": "35777888",
        "estado_anterior": None,
        "estado_nuevo": "PENDIENTE",
        "accion": "ALTA",
        "motivo": None,
        "id_operador": None,
    },
)

EVENTOS_VEHICULO: tuple[dict[str, Any], ...] = (
    {
        "patente": "AB123CD",
        "estado_anterior": None,
        "estado_nuevo": "PENDIENTE",
        "accion": "ALTA",
        "motivo": None,
        "id_operador": None,
    },
    {
        "patente": "AB123CD",
        "estado_anterior": "PENDIENTE",
        "estado_nuevo": "APROBADA",
        "accion": "APROBAR",
        "motivo": "Documentación del vehículo verificada.",
        "id_operador": ID_OPERADOR_SEED,
    },
    {
        "patente": "MOTO77",
        "estado_anterior": None,
        "estado_nuevo": "PENDIENTE",
        "accion": "ALTA",
        "motivo": None,
        "id_operador": None,
    },
    {
        "patente": "AC456EF",
        "estado_anterior": None,
        "estado_nuevo": "PENDIENTE",
        "accion": "ALTA",
        "motivo": None,
        "id_operador": None,
    },
)


def _upsert_conductor(session: Session, datos: dict[str, Any]) -> Conductor:
    conductor = session.scalar(select(Conductor).where(Conductor.dni == datos["dni"]))
    if conductor is None:
        conductor = Conductor(**datos)
        session.add(conductor)
    else:
        for campo, valor in datos.items():
            setattr(conductor, campo, valor)
    session.flush()
    return conductor


def _upsert_vehiculo(
    session: Session, datos: dict[str, Any], conductores: dict[str, Conductor]
) -> Vehiculo:
    base = {k: v for k, v in datos.items() if k not in {"dni_conductor", "tipos_servicio"}}
    base["id_conductor"] = conductores[datos["dni_conductor"]].id_conductor
    vehiculo = session.scalar(select(Vehiculo).where(Vehiculo.patente == datos["patente"]))
    if vehiculo is None:
        vehiculo = Vehiculo(**base)
        session.add(vehiculo)
    else:
        for campo, valor in base.items():
            setattr(vehiculo, campo, valor)
    session.flush()

    existentes = {
        item.tipo_servicio: item
        for item in session.scalars(
            select(VehiculoTipoServicio).where(
                VehiculoTipoServicio.id_vehiculo == vehiculo.id_vehiculo
            )
        )
    }
    for tipo_servicio, habilitado in datos["tipos_servicio"]:
        item = existentes.get(tipo_servicio)
        if item is None:
            session.add(
                VehiculoTipoServicio(
                    id_vehiculo=vehiculo.id_vehiculo,
                    tipo_servicio=tipo_servicio,
                    habilitado=habilitado,
                )
            )
        else:
            item.habilitado = habilitado
    session.flush()
    return vehiculo


def _upsert_documento(
    session: Session, datos: dict[str, Any], conductores: dict[str, Conductor]
) -> DocumentoConductor:
    base = dict(datos)
    dni = base.pop("dni_conductor")
    base["id_conductor"] = conductores[dni].id_conductor
    documento = session.scalar(
        select(DocumentoConductor).where(
            DocumentoConductor.id_conductor == base["id_conductor"],
            DocumentoConductor.tipo == "LICENCIA",
            DocumentoConductor.numero == base["numero"],
        )
    )
    if documento is None:
        documento = DocumentoConductor(tipo="LICENCIA", **base)
        session.add(documento)
    else:
        for campo, valor in base.items():
            setattr(documento, campo, valor)
    session.flush()
    return documento


def _asegurar_evento_conductor(
    session: Session, datos: dict[str, Any], conductores: dict[str, Conductor]
) -> None:
    id_conductor = conductores[datos["dni_conductor"]].id_conductor
    existe = session.scalar(
        select(HabilitacionEventoConductor.id_evento).where(
            HabilitacionEventoConductor.id_conductor == id_conductor,
            HabilitacionEventoConductor.accion == datos["accion"],
            HabilitacionEventoConductor.estado_nuevo == datos["estado_nuevo"],
        )
    )
    if existe is None:
        session.add(
            HabilitacionEventoConductor(
                id_conductor=id_conductor,
                estado_anterior=datos["estado_anterior"],
                estado_nuevo=datos["estado_nuevo"],
                accion=datos["accion"],
                motivo=datos["motivo"],
                id_operador=datos["id_operador"],
                fecha=FECHA_BASE,
            )
        )


def _asegurar_evento_vehiculo(
    session: Session, datos: dict[str, Any], vehiculos: dict[str, Vehiculo]
) -> None:
    id_vehiculo = vehiculos[datos["patente"]].id_vehiculo
    existe = session.scalar(
        select(HabilitacionEventoVehiculo.id_evento).where(
            HabilitacionEventoVehiculo.id_vehiculo == id_vehiculo,
            HabilitacionEventoVehiculo.accion == datos["accion"],
            HabilitacionEventoVehiculo.estado_nuevo == datos["estado_nuevo"],
        )
    )
    if existe is None:
        session.add(
            HabilitacionEventoVehiculo(
                id_vehiculo=id_vehiculo,
                estado_anterior=datos["estado_anterior"],
                estado_nuevo=datos["estado_nuevo"],
                accion=datos["accion"],
                motivo=datos["motivo"],
                id_operador=datos["id_operador"],
                fecha=FECHA_BASE,
            )
        )


def _contar(session: Session, modelo: type) -> int:
    return session.scalar(select(func.count()).select_from(modelo)) or 0


def cargar_datos(database_url: str | None = None) -> dict[str, int]:
    """Carga (o reconcilia) los datos de demostración y devuelve los totales."""

    engine = crear_engine(database_url)
    factory = crear_sessionmaker(engine)
    try:
        with factory.begin() as session:
            conductores = {datos["dni"]: _upsert_conductor(session, datos) for datos in CONDUCTORES}
            vehiculos = {
                datos["patente"]: _upsert_vehiculo(session, datos, conductores)
                for datos in VEHICULOS
            }
            for datos in DOCUMENTOS:
                _upsert_documento(session, datos, conductores)
            for datos in EVENTOS_CONDUCTOR:
                _asegurar_evento_conductor(session, datos, conductores)
            for datos in EVENTOS_VEHICULO:
                _asegurar_evento_vehiculo(session, datos, vehiculos)
            session.flush()

            return {
                "conductores": _contar(session, Conductor),
                "vehiculos": _contar(session, Vehiculo),
                "documentos": _contar(session, DocumentoConductor),
                "eventos_conductor": _contar(session, HabilitacionEventoConductor),
                "eventos_vehiculo": _contar(session, HabilitacionEventoVehiculo),
            }
    finally:
        engine.dispose()


if __name__ == "__main__":
    resumen = cargar_datos()
    print("Seed M3 aplicado:", resumen)
