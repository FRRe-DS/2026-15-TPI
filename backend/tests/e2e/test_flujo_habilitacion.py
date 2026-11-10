"""T601: flujo completo de habilitaci\u00f3n contra API y Keycloak reales.

Requiere el stack de Docker Compose levantado. Los tokens se obtienen del
endpoint OIDC del realm ``m3``; no se firman tokens de prueba. Cada ejecuci\u00f3n
usa un DNI y una patente exclusivos para no depender de datos previos.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import uuid4

import httpx
import pytest

pytestmark = pytest.mark.e2e

CONDUCTORES = "/api/v1/conductores"
MOTIVO_APROBACION_CONDUCTOR = "Licencia vigente y documentaci\u00f3n completa"
MOTIVO_APROBACION_VEHICULO = "Documentaci\u00f3n del veh\u00edculo validada"


def _dni_unico() -> str:
    return str(10_000_000 + uuid4().int % 90_000_000)


def _patente_unica() -> str:
    return f"E2E{uuid4().hex[:6].upper()}"


def _datos_conductor() -> dict[str, Any]:
    dni = _dni_unico()
    return {
        "dni": dni,
        "nombre": "Ana",
        "apellido": "G\u00f3mez",
        "telefono": "+5491176543210",
        "email": f"e2e.{dni}@example.com",
    }


def _datos_licencia() -> dict[str, str]:
    hoy = date.today()
    return {
        "tipo": "LICENCIA",
        "numero": f"LIC-{uuid4().hex[:8].upper()}",
        "categoria": "B1",
        "fecha_emision": (hoy - timedelta(days=365)).isoformat(),
        "fecha_vencimiento": (hoy + timedelta(days=365)).isoformat(),
        "url_archivo": "https://storage.example.com/licencias/e2e.pdf",
    }


def _datos_vehiculo() -> dict[str, Any]:
    return {
        "tipo": "AUTO",
        "patente": _patente_unica(),
        "marca": "Toyota",
        "modelo": "Corolla",
        "anio": 2022,
        "tipos_serv": ["PASAJEROS"],
    }


def _crear_conductor(
    cliente: httpx.Client,
    headers: dict[str, str],
) -> dict[str, Any]:
    respuesta = cliente.post(CONDUCTORES, json=_datos_conductor(), headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _registrar_licencia(
    cliente: httpx.Client,
    headers: dict[str, str],
    id_conductor: int,
) -> dict[str, Any]:
    respuesta = cliente.post(
        f"{CONDUCTORES}/{id_conductor}/documentacion",
        json=_datos_licencia(),
        headers=headers,
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _crear_vehiculo(
    cliente: httpx.Client,
    headers: dict[str, str],
    id_conductor: int,
) -> dict[str, Any]:
    respuesta = cliente.post(
        f"{CONDUCTORES}/{id_conductor}/vehiculos",
        json=_datos_vehiculo(),
        headers=headers,
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _consultar_habilitacion(
    cliente: httpx.Client,
    headers: dict[str, str],
    id_conductor: int,
) -> dict[str, Any]:
    respuesta = cliente.get(
        f"{CONDUCTORES}/{id_conductor}/habilitacion",
        headers=headers,
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_flujo_completo_de_habilitacion(
    cliente_api: httpx.Client,
    headers_operador: dict[str, str],
) -> None:
    conductor = _crear_conductor(cliente_api, headers_operador)
    id_conductor = conductor["id"]

    assert conductor["habilitacion"] == "PENDIENTE"
    assert conductor["documentos"] == []
    assert conductor["vehiculos"] == []

    licencia = _registrar_licencia(cliente_api, headers_operador, id_conductor)
    assert licencia["id_conductor"] == id_conductor
    assert licencia["tipo"] == "LICENCIA"
    assert licencia["estado"] == "VIGENTE"

    inicial = _consultar_habilitacion(cliente_api, headers_operador, id_conductor)
    assert inicial["estado"] == "PENDIENTE"
    assert [evento["estado"] for evento in inicial["historial"]] == ["PENDIENTE"]
    assert inicial["historial"][0]["motivo"] == "Alta del conductor"
    assert inicial["historial"][0]["id_operador"] is None

    vehiculo = _crear_vehiculo(cliente_api, headers_operador, id_conductor)
    id_vehiculo = vehiculo["id"]

    assert vehiculo["id_conductor"] == id_conductor
    assert vehiculo["habilitacion"] == "PENDIENTE"

    aprobacion_conductor = cliente_api.post(
        f"{CONDUCTORES}/{id_conductor}/habilitacion",
        json={"accion": "APROBAR", "motivo": MOTIVO_APROBACION_CONDUCTOR},
        headers=headers_operador,
    )
    assert aprobacion_conductor.status_code == 200, aprobacion_conductor.text

    cuerpo_conductor = aprobacion_conductor.json()
    assert cuerpo_conductor["id_conductor"] == id_conductor
    assert cuerpo_conductor["estado"] == "APROBADA"
    assert [evento["accion"] for evento in cuerpo_conductor["eventos"]] == [
        "ALTA",
        "APROBAR",
    ]

    alta_conductor, accion_conductor = cuerpo_conductor["eventos"]
    assert alta_conductor["estado_anterior"] is None
    assert alta_conductor["estado_nuevo"] == "PENDIENTE"
    assert accion_conductor["estado_anterior"] == "PENDIENTE"
    assert accion_conductor["estado_nuevo"] == "APROBADA"
    assert accion_conductor["motivo"] == MOTIVO_APROBACION_CONDUCTOR
    assert isinstance(accion_conductor["id_operador"], int)

    aprobacion_vehiculo = cliente_api.post(
        f"{CONDUCTORES}/{id_conductor}/vehiculos/{id_vehiculo}/habilitacion",
        json={"accion": "APROBAR", "motivo": MOTIVO_APROBACION_VEHICULO},
        headers=headers_operador,
    )
    assert aprobacion_vehiculo.status_code == 200, aprobacion_vehiculo.text

    cuerpo_vehiculo = aprobacion_vehiculo.json()
    assert cuerpo_vehiculo["id_vehiculo"] == id_vehiculo
    assert cuerpo_vehiculo["estado"] == "APROBADA"
    assert [evento["accion"] for evento in cuerpo_vehiculo["eventos"]] == [
        "ALTA",
        "APROBAR",
    ]

    alta_vehiculo, accion_vehiculo = cuerpo_vehiculo["eventos"]
    assert alta_vehiculo["estado_anterior"] is None
    assert alta_vehiculo["estado_nuevo"] == "PENDIENTE"
    assert accion_vehiculo["estado_anterior"] == "PENDIENTE"
    assert accion_vehiculo["estado_nuevo"] == "APROBADA"
    assert accion_vehiculo["motivo"] == MOTIVO_APROBACION_VEHICULO
    assert isinstance(accion_vehiculo["id_operador"], int)

    detalle_vehiculo = cliente_api.get(
        f"{CONDUCTORES}/{id_conductor}/vehiculos/{id_vehiculo}",
        headers=headers_operador,
    )
    assert detalle_vehiculo.status_code == 200, detalle_vehiculo.text
    assert detalle_vehiculo.json()["habilitacion"] == "APROBADA"

    historial = _consultar_habilitacion(cliente_api, headers_operador, id_conductor)
    assert historial["estado"] == "APROBADA"
    assert [evento["estado"] for evento in historial["historial"]] == [
        "PENDIENTE",
        "APROBADA",
    ]
    assert isinstance(historial["historial"][-1]["id_operador"], int)


def test_token_de_conductor_no_puede_aprobar(
    cliente_api: httpx.Client,
    headers_operador: dict[str, str],
    headers_conductor: dict[str, str],
) -> None:
    conductor = _crear_conductor(cliente_api, headers_operador)
    id_conductor = conductor["id"]
    antes = _consultar_habilitacion(cliente_api, headers_operador, id_conductor)

    respuesta = cliente_api.post(
        f"{CONDUCTORES}/{id_conductor}/habilitacion",
        json={"accion": "APROBAR", "motivo": "Intento con token de conductor"},
        headers=headers_conductor,
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "SIN_PERMISOS"

    despues = _consultar_habilitacion(cliente_api, headers_operador, id_conductor)
    assert despues == antes


def test_aprobacion_sin_licencia_vigente_no_cambia_estado_ni_historial(
    cliente_api: httpx.Client,
    headers_operador: dict[str, str],
) -> None:
    conductor = _crear_conductor(cliente_api, headers_operador)
    id_conductor = conductor["id"]
    antes = _consultar_habilitacion(cliente_api, headers_operador, id_conductor)
    assert antes["estado"] == "PENDIENTE"
    assert [evento["estado"] for evento in antes["historial"]] == ["PENDIENTE"]

    respuesta = cliente_api.post(
        f"{CONDUCTORES}/{id_conductor}/habilitacion",
        json={"accion": "APROBAR", "motivo": "Intento sin licencia vigente"},
        headers=headers_operador,
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "LICENCIA_VIGENTE_REQUERIDA"

    despues = _consultar_habilitacion(cliente_api, headers_operador, id_conductor)
    assert despues == antes
