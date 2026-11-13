import pytest
from app.api.configuracion import Settings
from pydantic import ValidationError

VARIABLES_REQUERIDAS = [
    "KEYCLOAK_URL",
    "KEYCLOAK_REALM",
    "DATABASE_URL",
    "RATE_LIMIT_HMAC_SECRET",
]


@pytest.fixture
def entorno_configuracion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
    monkeypatch.setenv("KEYCLOAK_REALM", "m3")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("REDIS_PASSWORD", "redis-secret-for-tests")
    monkeypatch.setenv(
        "RATE_LIMIT_HMAC_SECRET",
        "test-hmac-secret-shared-by-all-api-tests",
    )
    monkeypatch.setenv("RATE_LIMIT_ANON_REQUESTS", "60")
    monkeypatch.setenv("RATE_LIMIT_PREAUTH_REQUESTS", "1000")
    monkeypatch.setenv("RATE_LIMIT_AUTH_REQUESTS", "120")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/test_db",
    )


def test_configuracion_lee_variables_entorno(entorno_configuracion: None) -> None:
    settings = Settings(_env_file=None)

    assert settings.KEYCLOAK_URL == "http://localhost:8080"
    assert settings.KEYCLOAK_REALM == "m3"
    assert settings.REDIS_URL == "redis://localhost:6379/0"
    assert settings.REDIS_PASSWORD.get_secret_value() == "redis-secret-for-tests"
    assert (
        settings.RATE_LIMIT_HMAC_SECRET.get_secret_value()
        == "test-hmac-secret-shared-by-all-api-tests"
    )
    assert settings.RATE_LIMIT_ANON_REQUESTS == 60
    assert settings.RATE_LIMIT_PREAUTH_REQUESTS == 1000
    assert settings.RATE_LIMIT_AUTH_REQUESTS == 120
    assert settings.RATE_LIMIT_WINDOW_SECONDS == 60
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


@pytest.mark.parametrize(
    ("variable", "valor"),
    [
        ("RATE_LIMIT_ANON_REQUESTS", "0"),
        ("RATE_LIMIT_PREAUTH_REQUESTS", "0"),
        ("RATE_LIMIT_AUTH_REQUESTS", "-1"),
        ("RATE_LIMIT_WINDOW_SECONDS", "no-es-entero"),
    ],
)
def test_configuracion_rechaza_limites_invalidos(
    variable: str,
    valor: str,
    entorno_configuracion: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(variable, valor)

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)

    assert variable in str(error.value)


def test_configuracion_lee_limites_positivos(
    entorno_configuracion: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RATE_LIMIT_ANON_REQUESTS", "10")
    monkeypatch.setenv("RATE_LIMIT_PREAUTH_REQUESTS", "30")
    monkeypatch.setenv("RATE_LIMIT_AUTH_REQUESTS", "20")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "30")

    settings = Settings(_env_file=None)

    assert settings.RATE_LIMIT_ANON_REQUESTS == 10
    assert settings.RATE_LIMIT_PREAUTH_REQUESTS == 30
    assert settings.RATE_LIMIT_AUTH_REQUESTS == 20
    assert settings.RATE_LIMIT_WINDOW_SECONDS == 30


def test_error_de_configuracion_no_revela_password_redis(
    entorno_configuracion: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RATE_LIMIT_AUTH_REQUESTS", "secreto-invalidante")

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)

    assert "redis-secret-for-tests" not in str(error.value)


def test_configuracion_rechaza_secreto_hmac_corto(
    entorno_configuracion: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RATE_LIMIT_HMAC_SECRET", "corto")

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)

    assert "RATE_LIMIT_HMAC_SECRET" in str(error.value)
    assert "corto" not in str(error.value)
