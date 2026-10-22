from pydantic import BaseModel


class Error(BaseModel):
    """Cuerpo único de error de la API."""

    codigo: str
    mensaje: str
