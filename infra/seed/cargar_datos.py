"""Carga determinista e idempotente de datos de demostración de M3.

El script puede ejecutarse todas las veces que sea necesario: identifica cada
registro por su clave natural (DNI, patente, número de licencia, tipo de
servicio, viaje o evento) y sólo inserta o reconcilia lo que falta.

Uso:
    DATABASE_URL=postgresql+psycopg://... python infra/seed/cargar_datos.py
"""

from __future__ import annotations

import sys
from datetime import UTC, date, datetime, timedelta
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
    Solicitud,
    Vehiculo,
    VehiculoDocumento,
    VehiculoTipoServicio,
)
from app.infraestructura.db.sesion import crear_engine, crear_sessionmaker  # noqa: E402

FECHA_BASE = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
FECHA_VIGENTE = date(2035, 12, 31)
FECHA_VENCIDA = date(2020, 12, 31)
FECHA_EMISION = date(2024, 1, 1)
FECHA_EMISION_VENCIDA = date(2016, 1, 1)
SOLICITUD_VIGENTE_HASTA = datetime(2035, 12, 31, 23, 59, tzinfo=UTC)
SOLICITUD_VENCIDA_DESDE = datetime(2020, 12, 31, 23, 59, tzinfo=UTC)
ID_OPERADOR_SEED = 101

CONDUCTORES: tuple[dict[str, Any], ...] = (
    {
        "dni": "30111222",
        "nombre": "Ana",
        "apellido": "Pérez",
        "telefono": "+5493624000001",
        "email": "ana.perez@m3.local",
        "estado_habilitacion": "APROBADA",
        "estado": "CONECTADO",
        "fecha_ultimo_cambio_estado": FECHA_BASE,
        "suma_puntajes": 20,
        "cantidad_calificaciones": 4,
        "latitud": -31.6107,
        "longitud": -60.6973,
        "fecha_act_ubic": FECHA_BASE,
    },
    {
        "dni": "28444555",
        "nombre": "Bruno",
        "apellido": "Gómez",
        "telefono": "+5493624000002",
        "email": "bruno.gomez@m3.local",
        "estado_habilitacion": "APROBADA",
        "estado": "DISPONIBLE",
        "fecha_ultimo_cambio_estado": FECHA_BASE,
        "suma_puntajes": 0,
        "cantidad_calificaciones": 0,
        "latitud": -32.9468,
        "longitud": -60.6393,
        "fecha_act_ubic": FECHA_BASE,
    },
    {
        "dni": "35777888",
        "nombre": "Carla",
        "apellido": "Díaz",
        "telefono": "+5493624000003",
        "email": "carla.diaz@m3.local",
        "estado_habilitacion": "PENDIENTE",
        "estado": "DESCONECTADO",
        "fecha_ultimo_cambio_estado": None,
        "suma_puntajes": 0,
        "cantidad_calificaciones": 0,
        "latitud": None,
        "longitud": None,
        "fecha_act_ubic": None,
    },
    {
        "dni": "40123456",
        "nombre": "Diego",
        "apellido": "Sosa",
        "telefono": "+5493624000004",
        "email": "diego.sosa@m3.local",
        "estado_habilitacion": "APROBADA",
        "estado": "OCUPADO",
        "fecha_ultimo_cambio_estado": FECHA_BASE,
        "suma_puntajes": 12,
        "cantidad_calificaciones": 3,
        "latitud": -31.7333,
        "longitud": -60.5297,
        "fecha_act_ubic": FECHA_BASE,
    },
)

VEHICULO_ACTIVO: dict[str, str] = {
    "30111222": "AB123CD",
    "28444555": "MOTO77",
    "40123456": "AC999ZZ",
}

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
        "estado_habilitacion": "APROBADA",
        "tipos_servicio": (("PASAJEROS", True),),
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
    {
        "dni_conductor": "40123456",
        "patente": "AC999ZZ",
        "marca": "Volkswagen",
        "modelo": "Vento",
        "anio": 2020,
        "tipo": "AUTO",
        "estado_habilitacion": "APROBADA",
        "tipos_servicio": (("PASAJEROS", True), ("ENVIOS", True)),
    },
)

DOCUMENTOS: tuple[dict[str, Any], ...] = (
    {
        "dni_conductor": "30111222",
        "numero": "LIC-30111222",
        "categoria": "B1",
        "fecha_emision": FECHA_EMISION,
        "fecha_vencimiento": FECHA_VIGENTE,
        "url_archivo": "https://documentos.m3.local/licencias/30111222.pdf",
    },
    {
        "dni_conductor": "28444555",
        "numero": "LIC-28444555",
        "categoria": "A2",
        "fecha_emision": FECHA_EMISION,
        "fecha_vencimiento": FECHA_VIGENTE,
        "url_archivo": "https://documentos.m3.local/licencias/28444555.pdf",
    },
    {
        "dni_conductor": "35777888",
        "numero": "LIC-35777888",
        "categoria": "B1",
        "fecha_emision": FECHA_EMISION_VENCIDA,
        "fecha_vencimiento": FECHA_VENCIDA,
        "url_archivo": "https://documentos.m3.local/licencias/35777888.pdf",
    },
    {
        "dni_conductor": "40123456",
        "numero": "LIC-40123456",
        "categoria": "B1",
        "fecha_emision": FECHA_EMISION,
        "fecha_vencimiento": FECHA_VIGENTE,
        "url_archivo": "https://documentos.m3.local/licencias/40123456.pdf",
    },
)

DOCUMENTOS_VEHICULO: tuple[dict[str, Any], ...] = (
    {
        "patente": "AB123CD",
        "tipo": "SEGURO",
        "numero": "SEG-AB123CD",
        "entidad_emisora": "La Segunda",
        "fecha_emision": FECHA_EMISION,
        "fecha_vencimiento": FECHA_VIGENTE,
        "url_archivo": "https://documentos.m3.local/vehiculos/AB123CD-seguro.pdf",
    },
    {
        "patente": "AB123CD",
        "tipo": "VTV",
        "numero": "VTV-AB123CD",
        "entidad_emisora": "Municipalidad de Santa Fe",
        "fecha_emision": FECHA_EMISION_VENCIDA,
        "fecha_vencimiento": FECHA_VENCIDA,
        "url_archivo": "https://documentos.m3.local/vehiculos/AB123CD-vtv.pdf",
    },
    {
        "patente": "MOTO77",
        "tipo": "SEGURO",
        "numero": "SEG-MOTO77",
        "entidad_emisora": "Río Negro",
        "fecha_emision": FECHA_EMISION,
        "fecha_vencimiento": FECHA_VIGENTE,
        "url_archivo": "https://documentos.m3.local/vehiculos/MOTO77-seguro.pdf",
    },
)

SOLICITUDES: tuple[dict[str, Any], ...] = (
    {
        "id_viaje": 1001,
        "dni_conductor": "30111222",
        "estado": "PENDIENTE",
        "vence_en": SOLICITUD_VIGENTE_HASTA,
        "respuesta": None,
        "hora_rta": None,
    },
    {
        "id_viaje": 1002,
        "dni_conductor": "30111222",
        "estado": "PENDIENTE",
        "vence_en": SOLICITUD_VENCIDA_DESDE,
        "respuesta": None,
        "hora_rta": None,
    },
    {
        "id_viaje": 1003,
        "dni_conductor": "40123456",
        "estado": "ACEPTADO",
        "vence_en": FECHA_BASE + timedelta(days=1),
        "respuesta": "ACEPTADO",
        "hora_rta": FECHA_BASE - timedelta(hours=1),
    },
    {
        "id_viaje": 1004,
        "dni_conductor": "28444555",
        "estado": "RECHAZADO",
        "vence_en": FECHA_BASE + timedelta(days=1),
        "respuesta": "RECHAZADO",
        "hora_rta": FECHA_BASE - timedelta(minutes=30),
    },
    {
        "id_viaje": 1005,
        "dni_conductor": "35777888",
        "estado": "VENCIDA",
        "vence_en": FECHA_BASE - timedelta(days=1),
        "respuesta": None,
        "hora_rta": None,
    },
)

EVENTOS_CONDUCTOR: tuple[dict[str, Any], ...] = (
    {
        "dni_conductor": "30111222",
        "estado_anterior": None,
        "estado_nuevo": "PENDIENTE",
        "accion": "ALTA",
        "motivo": "Alta inicial registrada por el sistema.",
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
        "motivo": "Alta inicial registrada por el sistema.",
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
        "dni_conductor": "28444555",
        "estado_anterior": "OBSERVADA",
        "estado_nuevo": "APROBADA",
        "accion": "APROBAR",
        "motivo": "Licencia renovada y documentación verificada.",
        "id_operador": ID_OPERADOR_SEED,
    },
    {
        "dni_conductor": "35777888",
        "estado_anterior": None,
        "estado_nuevo": "PENDIENTE",
        "accion": "ALTA",
        "motivo": "Alta inicial registrada por el sistema.",
        "id_operador": None,
    },
    {
        "dni_conductor": "40123456",
        "estado_anterior": None,
        "estado_nuevo": "PENDIENTE",
        "accion": "ALTA",
        "motivo": "Alta inicial registrada por el sistema.",
        "id_operador": None,
    },
    {
        "dni_conductor": "40123456",
        "estado_anterior": "PENDIENTE",
        "estado_nuevo": "APROBADA",
        "accion": "APROBAR",
        "motivo": "Documentación verificada.",
        "id_operador": ID_OPERADOR_SEED,
    },
)

EVENTOS_VEHICULO: tuple[dict[str, Any], ...] = (
    {
        "patente": "AB123CD",
        "estado_anterior": None,
        "estado_nuevo": "PENDIENTE",
        "accion": "ALTA",
        "motivo": "Alta inicial registrada por el sistema.",
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
        "motivo": "Alta inicial registrada por el sistema.",
        "id_operador": None,
    },
    {
        "patente": "MOTO77",
        "estado_anterior": "PENDIENTE",
        "estado_nuevo": "APROBADA",
        "accion": "APROBAR",
        "motivo": "Documentación del vehículo verificada.",
        "id_operador": ID_OPERADOR_SEED,
    },
    {
        "patente": "AC456EF",
        "estado_anterior": None,
        "estado_nuevo": "PENDIENTE",
        "accion": "ALTA",
        "motivo": "Alta inicial registrada por el sistema.",
        "id_operador": None,
    },
    {
        "patente": "AC999ZZ",
        "estado_anterior": None,
        "estado_nuevo": "PENDIENTE",
        "accion": "ALTA",
        "motivo": "Alta inicial registrada por el sistema.",
        "id_operador": None,
    },
    {
        "patente": "AC999ZZ",
        "estado_anterior": "PENDIENTE",
        "estado_nuevo": "APROBADA",
        "accion": "APROBAR",
        "motivo": "Documentación del vehículo verificada.",
        "id_operador": ID_OPERADOR_SEED,
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


def _upsert_documento_vehiculo(
    session: Session, datos: dict[str, Any], vehiculos: dict[str, Vehiculo]
) -> VehiculoDocumento:
    base = dict(datos)
    patente = base.pop("patente")
    base["id_vehiculo"] = vehiculos[patente].id_vehiculo
    documento = session.scalar(
        select(VehiculoDocumento).where(
            VehiculoDocumento.id_vehiculo == base["id_vehiculo"],
            VehiculoDocumento.tipo == base["tipo"],
            VehiculoDocumento.numero == base["numero"],
        )
    )
    if documento is None:
        documento = VehiculoDocumento(**base)
        session.add(documento)
    session.flush()
    return documento


def _upsert_solicitud(
    session: Session, datos: dict[str, Any], conductores: dict[str, Conductor]
) -> Solicitud:
    base = dict(datos)
    dni = base.pop("dni_conductor")
    base["id_conductor"] = conductores[dni].id_conductor
    solicitud = session.scalar(
        select(Solicitud).where(
            Solicitud.id_conductor == base["id_conductor"],
            Solicitud.id_viaje == base["id_viaje"],
        )
    )
    if solicitud is None:
        solicitud = Solicitud(**base)
        session.add(solicitud)
    else:
        for campo, valor in base.items():
            setattr(solicitud, campo, valor)
    session.flush()
    return solicitud


def _asignar_vehiculo_activo(
    session: Session,
    conductores: dict[str, Conductor],
    vehiculos: dict[str, Vehiculo],
) -> None:
    for dni, conductor in conductores.items():
        patente = VEHICULO_ACTIVO.get(dni)
        conductor.id_vehiculo_activo = (
            vehiculos[patente].id_vehiculo if patente is not None else None
        )
    session.flush()


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
            _asignar_vehiculo_activo(session, conductores, vehiculos)
            for datos in DOCUMENTOS:
                _upsert_documento(session, datos, conductores)
            for datos in DOCUMENTOS_VEHICULO:
                _upsert_documento_vehiculo(session, datos, vehiculos)
            for datos in SOLICITUDES:
                _upsert_solicitud(session, datos, conductores)
            for datos in EVENTOS_CONDUCTOR:
                _asegurar_evento_conductor(session, datos, conductores)
            for datos in EVENTOS_VEHICULO:
                _asegurar_evento_vehiculo(session, datos, vehiculos)
            session.flush()

            return {
                "conductores": _contar(session, Conductor),
                "vehiculos": _contar(session, Vehiculo),
                "documentos": _contar(session, DocumentoConductor),
                "documentos_vehiculo": _contar(session, VehiculoDocumento),
                "solicitudes": _contar(session, Solicitud),
                "eventos_conductor": _contar(session, HabilitacionEventoConductor),
                "eventos_vehiculo": _contar(session, HabilitacionEventoVehiculo),
            }
    finally:
        engine.dispose()


if __name__ == "__main__":
    resumen = cargar_datos()
    print("Seed M3 aplicado:", resumen)
