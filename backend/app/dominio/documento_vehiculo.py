"""Documento del vehiculo: seguro, cedula verde o VTV (US6).

Se valida al registrar y su estado `VIGENTE` o `VENCIDO` no se guarda: se calcula con la
fecha de hoy, igual que el documento del conductor.
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum

from app.dominio.documento import EstadoDocumento, es_url_valida
from app.dominio.errores import DatosInvalidos
from app.dominio.validaciones import exigir_texto


class TipoDocumentoVehiculo(Enum):
    SEGURO = "SEGURO"
    CEDULA_VERDE = "CEDULA_VERDE"
    VTV = "VTV"


@dataclass
class DocumentoVehiculo:
    tipo: TipoDocumentoVehiculo
    numero: str
    entidad_emisora: str | None
    fecha_emision: date
    fecha_vencimiento: date
    url_archivo: str
    id: int | None = None

    @classmethod
    def crear(
        cls,
        *,
        tipo: TipoDocumentoVehiculo,
        numero: str,
        entidad_emisora: str | None,
        fecha_emision: date,
        fecha_vencimiento: date,
        url_archivo: str,
    ) -> "DocumentoVehiculo":
        exigir_texto("numero", numero)
        if fecha_vencimiento <= fecha_emision:
            raise DatosInvalidos("La fecha de vencimiento debe ser posterior a la de emisión")
        if not es_url_valida(url_archivo):
            raise DatosInvalidos("La URL del archivo no es válida")
        return cls(
            tipo=tipo,
            numero=numero,
            entidad_emisora=entidad_emisora,
            fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_vencimiento,
            url_archivo=url_archivo,
        )

    def estado_al(self, hoy: date) -> EstadoDocumento:
        if self.fecha_vencimiento >= hoy:
            return EstadoDocumento.VIGENTE
        return EstadoDocumento.VENCIDO
