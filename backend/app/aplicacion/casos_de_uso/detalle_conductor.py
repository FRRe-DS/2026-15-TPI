from collections.abc import Sequence
from datetime import date

from app.aplicacion.casos_de_uso.resultados import ConductorDetalle, DocumentoConEstado
from app.aplicacion.puertos.reloj import Reloj
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.conductor import Conductor
from app.dominio.documento import Documento


def _con_estado(documentos: list[Documento], hoy: date) -> list[DocumentoConEstado]:
    return [DocumentoConEstado(documento, documento.estado_al(hoy)) for documento in documentos]


def armar_detalle(uow: UnidadDeTrabajo, reloj: Reloj, conductor: Conductor) -> ConductorDetalle:
    documentos = uow.documentos.listar_por_conductor(conductor.id)
    vehiculos = uow.vehiculos.listar_por_conductor(conductor.id)
    return ConductorDetalle(conductor, _con_estado(documentos, reloj.hoy()), vehiculos)


def armar_detalles(
    uow: UnidadDeTrabajo, reloj: Reloj, conductores: Sequence[Conductor]
) -> list[ConductorDetalle]:
    # Dos consultas por lote (vehiculos y documentos) sin importar cuantos conductores sean.
    if not conductores:
        return []
    ids = [conductor.id for conductor in conductores]
    vehiculos_por_conductor = uow.vehiculos.listar_por_conductores(ids)
    documentos_por_conductor = uow.documentos.listar_por_conductores(ids)
    hoy = reloj.hoy()
    return [
        ConductorDetalle(
            conductor,
            _con_estado(documentos_por_conductor[conductor.id], hoy),
            vehiculos_por_conductor[conductor.id],
        )
        for conductor in conductores
    ]
