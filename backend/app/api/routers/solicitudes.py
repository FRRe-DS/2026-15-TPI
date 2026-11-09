from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencias import (
    obtener_caso_listar_solicitudes_conductor,
    obtener_caso_responder_solicitud,
)
from app.api.esquemas.solicitud import (
    EstadoSolicitud,
    RespuestaSolicitudRequest,
    Solicitud,
    solicitud_desde_dominio,
)
from app.api.seguridad import (
    requerir_conductor_propio_u_operador,
    requerir_operador_o_conductor,
)
from app.aplicacion.casos_de_uso.listar_solicitudes_conductor import ListarSolicitudesConductor
from app.aplicacion.casos_de_uso.responder_solicitud import ResponderSolicitud
from app.aplicacion.politicas.acceso import Identidad
from app.dominio.solicitud import EstadoSolicitud as EstadoSolicitudDominio

router = APIRouter(tags=["Solicitudes"])


@router.get(
    "/conductores/{id_conductor}/solicitudes",
    response_model=list[Solicitud],
    operation_id="listarSolicitudesConductor",
    dependencies=[Depends(requerir_conductor_propio_u_operador)],
)
def listar_solicitudes(
    id_conductor: int,
    caso: Annotated[ListarSolicitudesConductor, Depends(obtener_caso_listar_solicitudes_conductor)],
    estado: EstadoSolicitud | None = None,
) -> list[Solicitud]:
    solicitudes = caso.ejecutar(
        id_conductor=id_conductor,
        estado=EstadoSolicitudDominio(estado.value) if estado is not None else None,
    )
    return [solicitud_desde_dominio(solicitud) for solicitud in solicitudes]


@router.post(
    "/solicitudes/{id_solicitud}",
    response_model=Solicitud,
    operation_id="responderSolicitud",
)
def responder_solicitud(
    id_solicitud: int,
    datos: RespuestaSolicitudRequest,
    # El dueño de la solicitud se conoce al leerla: el caso de uso verifica que el
    # conductor sea el dueño. Acá solo se descarta al rol servicio, que no escribe.
    identidad: Annotated[Identidad, Depends(requerir_operador_o_conductor)],
    caso: Annotated[ResponderSolicitud, Depends(obtener_caso_responder_solicitud)],
) -> Solicitud:
    solicitud = caso.ejecutar(
        id_solicitud=id_solicitud,
        respuesta=EstadoSolicitudDominio(datos.respuesta.value),
        hora_rta=datos.hora_rta,
        identidad=identidad,
    )
    return solicitud_desde_dominio(solicitud)
