from dataclasses import dataclass
from datetime import date
from enum import Enum
from urllib.parse import urlparse

from app.dominio.errores import DatosInvalidos
from app.dominio.validaciones import exigir_texto


class TipoDocumento(Enum):
    LICENCIA = "LICENCIA"


class EstadoDocumento(Enum):
    VIGENTE = "VIGENTE"
    VENCIDO = "VENCIDO"


ESQUEMAS_DE_URL_PERMITIDOS = frozenset({"http", "https"})


def es_url_valida(url: str) -> bool:
    """Solo `http` y `https` con host: el frontend la muestra como enlace."""
    partes = urlparse(url)
    return partes.scheme in ESQUEMAS_DE_URL_PERMITIDOS and bool(partes.netloc)


@dataclass
class Documento:
    tipo: TipoDocumento
    numero: str
    categoria: str | None
    fecha_emision: date
    fecha_vencimiento: date
    url_archivo: str
    id: int | None = None

    @classmethod
    def crear(
        cls,
        *,
        tipo: TipoDocumento,
        numero: str,
        categoria: str | None,
        fecha_emision: date,
        fecha_vencimiento: date,
        url_archivo: str,
    ) -> "Documento":
        exigir_texto("numero", numero)
        if fecha_vencimiento <= fecha_emision:
            raise DatosInvalidos("La fecha de vencimiento debe ser posterior a la de emisión")
        if not es_url_valida(url_archivo):
            raise DatosInvalidos("La URL del archivo no es válida")
        return cls(
            tipo=tipo,
            numero=numero,
            categoria=categoria,
            fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_vencimiento,
            url_archivo=url_archivo,
        )

    def estado_al(self, hoy: date) -> EstadoDocumento:
        if self.fecha_vencimiento >= hoy:
            return EstadoDocumento.VIGENTE
        return EstadoDocumento.VENCIDO
