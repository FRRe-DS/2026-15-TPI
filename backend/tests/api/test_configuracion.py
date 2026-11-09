import pytest
from app.api.configuracion import Settings
from pydantic import ValidationError

VARIABLES_REQUERIDAS = [
    "KEYCLOAK_URL",
    "KEYCLOAK_REALM",
    "DATABASE_URL",
]


@pytest.fixture
def entorno_configuracion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
    monkeypatch.setenv("KEYCLOAK_REALM", "m3")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/test_db",
    )


def test_configuracion_lee_variables_entorno(entorno_configuracion: None) -> None:
    settings = Settings(_env_file=None)

    assert settings.KEYCLOAK_URL == "http://localhost:8080"
    assert settings.KEYCLOAK_REALM == "m3"
    assert settings.DATABASE_URL == "postgresql+psycopg://test:test@localhost:5432/test_db"


@pytest.mark.parametrize("variable", VARIABLES_REQUERIDAS)
def test_configuracion_falla_si_falta_variable(
    variable: str,
    entorno_configuracion: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(variable)

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)

    assert variable in str(error.value), (
        f"El error debe identificar la variable faltante: {variable}"
    )


def test_ubicacion_simulada_tiene_valores_por_defecto(entorno_configuracion: None) -> None:
    settings = Settings(_env_file=None)

    assert settings.UBICACION_SIMULADA_LATITUD == -27.4511
    assert settings.UBICACION_SIMULADA_LONGITUD == -58.9867


def test_ubicacion_simulada_se_puede_cambiar_por_entorno(
    entorno_configuracion: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UBICACION_SIMULADA_LATITUD", "-31.4")
    monkeypatch.setenv("UBICACION_SIMULADA_LONGITUD", "-64.2")

    settings = Settings(_env_file=None)

    assert settings.UBICACION_SIMULADA_LATITUD == -31.4
    assert settings.UBICACION_SIMULADA_LONGITUD == -64.2


@pytest.mark.parametrize(
    ("variable", "valor"),
    [
        ("UBICACION_SIMULADA_LATITUD", "90.1"),
        ("UBICACION_SIMULADA_LATITUD", "-90.1"),
        ("UBICACION_SIMULADA_LONGITUD", "180.1"),
        ("UBICACION_SIMULADA_LONGITUD", "-180.1"),
    ],
)
def test_ubicacion_simulada_fuera_de_rango_es_un_error(
    variable: str,
    valor: str,
    entorno_configuracion: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(variable, valor)

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)

    assert variable in str(error.value)


def test_ubicacion_simulada_cero_cero_es_un_error_de_configuracion(
    entorno_configuracion: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UBICACION_SIMULADA_LATITUD", "0")
    monkeypatch.setenv("UBICACION_SIMULADA_LONGITUD", "0")

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)

    assert "UBICACION_SIMULADA_LATITUD" in str(error.value)
    assert "UBICACION_SIMULADA_LONGITUD" in str(error.value)
