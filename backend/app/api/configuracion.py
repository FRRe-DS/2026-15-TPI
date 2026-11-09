from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la API obtenida del entorno.

    Las tres variables son obligatorias. Si falta alguna, Pydantic muestra un
    ``ValidationError`` indicando el nombre exacto del campo faltante.
    """

    KEYCLOAK_PUBLIC_URL: str | None = None
    KEYCLOAK_URL: str
    KEYCLOAK_REALM: str
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: SecretStr = SecretStr("")
    RATE_LIMIT_ANON_REQUESTS: int = Field(default=60, gt=0)
    RATE_LIMIT_PREAUTH_REQUESTS: int = Field(default=1000, gt=0)
    RATE_LIMIT_AUTH_REQUESTS: int = Field(default=120, gt=0)
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, gt=0)
    # Ubicación que M3 asigna cuando el conductor sale de DESCONECTADO sin informar la suya.
    UBICACION_SIMULADA_LATITUD: float = Field(default=-27.4511, ge=-90, le=90)
    UBICACION_SIMULADA_LONGITUD: float = Field(default=-58.9867, ge=-180, le=180)

    @model_validator(mode="after")
    def _ubicacion_simulada_no_es_cero_cero(self) -> "Settings":
        if self.UBICACION_SIMULADA_LATITUD == 0 and self.UBICACION_SIMULADA_LONGITUD == 0:
            raise ValueError(
                "UBICACION_SIMULADA_LATITUD y UBICACION_SIMULADA_LONGITUD no pueden ser 0, 0"
            )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def obtener_configuracion() -> Settings:
    """Carga la configuración y valida las variables obligatorias."""
    return Settings()
