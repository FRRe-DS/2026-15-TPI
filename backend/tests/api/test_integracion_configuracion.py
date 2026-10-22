from app.api import dependencias
from app.api.configuracion import Settings
from app.api.seguridad import obtener_cliente_jwks
from app.infraestructura.repositorios.sql_unidad_de_trabajo import SqlUnidadDeTrabajo
from sqlalchemy.orm import sessionmaker


def test_dependencia_construye_la_unidad_sql_real(monkeypatch):
    fabrica = sessionmaker()
    monkeypatch.setattr(dependencias, "_fabrica_de_sesiones", lambda: fabrica)
    unidad = next(dependencias.obtener_unidad_de_trabajo())
    assert isinstance(unidad, SqlUnidadDeTrabajo)
    with unidad:
        assert unidad._sesion.bind is None


def test_jwks_usa_la_url_interna(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_PUBLIC_URL", "http://localhost:8081")
    settings = Settings(
        KEYCLOAK_URL="http://keycloak:8080", KEYCLOAK_REALM="m3", DATABASE_URL="test"
    )
    cliente = obtener_cliente_jwks(settings)
    assert cliente.uri == "http://keycloak:8080/realms/m3/protocol/openid-connect/certs"
