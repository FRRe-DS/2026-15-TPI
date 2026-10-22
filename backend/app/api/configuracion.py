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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def obtener_configuracion() -> Settings:
    """Carga la configuración y valida las variables obligatorias."""
    return Settings()
