from app.aplicacion.casos_de_uso.resultados import ConductorDetalle, DocumentoConEstado
from app.aplicacion.puertos.reloj import Reloj
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.conductor import Conductor


def armar_detalle(uow: UnidadDeTrabajo, reloj: Reloj, conductor: Conductor) -> ConductorDetalle:
    # Limite conocido: 2 consultas por conductor (los puertos no tienen metodos por lote).
    hoy = reloj.hoy()
    documentos = [
        DocumentoConEstado(documento, documento.estado_al(hoy))
        for documento in uow.documentos.listar_por_conductor(conductor.id)
    ]
    vehiculos = uow.vehiculos.listar_por_conductor(conductor.id)
    return ConductorDetalle(conductor, documentos, vehiculos)
