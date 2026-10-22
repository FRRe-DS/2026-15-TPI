
import pytest
from pydantic import ValidationError

from app.api.configuracion import Settings


VARIABLES_REQUERIDAS = [
    "KEYCLOAK_URL",
    "KEYCLOAK_REALM",
    "DATABASE_URL",
]


@pytest.fixture
def entorno_configuracion(monkeypatch):
    """Prepara las variables de entorno para las pruebas."""
    monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
    monkeypatch.setenv("KEYCLOAK_REALM", "m3")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/test_db",
    )


def test_configuracion_lee_variables_entorno(entorno_configuracion):
    settings = Settings(_env_file=None)

    assert settings.KEYCLOAK_URL == "http://localhost:8080"
    assert settings.KEYCLOAK_REALM == "m3"
    assert settings.DATABASE_URL == (
        "postgresql+psycopg://test:test@localhost:5432/test_db"
    )


@pytest.mark.parametrize("variable", VARIABLES_REQUERIDAS)
def test_configuracion_falla_si_falta_variable(
    variable,
    entorno_configuracion,
    monkeypatch,
):
    monkeypatch.delenv(variable)

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)

    assert variable in str(error.value), (
        f"El error debe identificar la variable faltante: {variable}"
    )