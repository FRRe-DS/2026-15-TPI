"""Lecturas de M4: API real, casos de uso y PostgreSQL, sin simular repositorios."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from app.api import dependencias
from app.api.main import crear_app
from app.api.seguridad import obtener_cliente_jwks
from app.infraestructura.db.modelos import Conductor
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

FECHA_UBICACION = datetime(2026, 10, 22, 15, 0, tzinfo=UTC)


@pytest.fixture
def cliente_m4(monkeypatch, fabrica_sesiones):
    monkeypatch.setenv("KEYCLOAK_URL", "http://keycloak:8080")
    monkeypatch.setenv("KEYCLOAK_REALM", "m3")
    monkeypatch.setenv("KEYCLOAK_PUBLIC_URL", "http://localhost:8081")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://prueba:prueba@localhost/m3")
    monkeypatch.setattr(dependencias, "_fabrica_de_sesiones", lambda: fabrica_sesiones)
    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(
        {
            "iss": "http://localhost:8081/realms/m3",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "realm_access": {"roles": ["conductor"]},
        },
        clave,
        algorithm="RS256",
    )
    app = crear_app()
    app.dependency_overrides[obtener_cliente_jwks] = lambda: SimpleNamespace(
        get_signing_key_from_jwt=lambda _: SimpleNamespace(key=clave.public_key())
    )
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as cliente:
        yield cliente


@pytest.mark.parametrize("detalle", [False, True], ids=["listado", "detalle"])
@pytest.mark.parametrize("con_ubicacion", [False, True], ids=["sin-ubicacion", "ubicado"])
def test_get_devuelve_disponibilidad_y_ubicacion_persistidas(
    cliente_m4, sesion_bd, detalle, con_ubicacion
):
    ubicacion = (
        {"latitud": -27.4511, "longitud": -58.9867, "fecha_act_ubic": FECHA_UBICACION}
        if con_ubicacion
        else {"latitud": None, "longitud": None, "fecha_act_ubic": None}
    )
    conductor = Conductor(
        dni="30123456",
        nombre="Ana",
        apellido="Perez",
        telefono="3794000000",
        email="ana@example.com",
        estado_habilitacion="APROBADA",
        conectado=True,
        disponible=True,
        **ubicacion,
    )
    no_disponible = Conductor(
        dni="30123457",
        nombre="Bruno",
        apellido="Gomez",
        telefono="3794000001",
        email="bruno@example.com",
        estado_habilitacion="PENDIENTE",
        conectado=False,
        disponible=False,
    )
    sesion_bd.add_all([conductor, no_disponible])
    sesion_bd.commit()
    ruta = (
        f"/api/v1/conductores/{conductor.id_conductor}"
        if detalle
        else "/api/v1/conductores?disponible=true&habilitado=true"
    )
    respuesta = cliente_m4.get(ruta)
    assert respuesta.status_code == 200
    datos = respuesta.json()
    if not detalle:
        assert len(datos) == 1
        datos = datos[0]
    assert datos["id"] == conductor.id_conductor
    assert datos["conectado"] is True
    assert datos["disponible"] is True
    assert datos["latitud"] == ubicacion["latitud"]
    assert datos["longitud"] == ubicacion["longitud"]
    if con_ubicacion:
        assert datetime.fromisoformat(datos["fecha_act_ubic"]) == FECHA_UBICACION
    else:
        assert datos["fecha_act_ubic"] is None
