from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencias import (
    obtener_caso_actualizar_estado_conductor,
    obtener_caso_obtener_estado_conductor,
    obtener_caso_obtener_ubicacion_conductor,
)
from app.api.esquemas.estado import (
    EstadoConductor,
    EstadoConductorRequest,
    UbicacionConductor,
    estado_desde_dominio,
    ubicacion_desde_dominio,
)
from app.api.seguridad import (
    requerir_conductor_propio_operador_o_servicio,
    requerir_conductor_propio_u_operador,
)
from app.aplicacion.casos_de_uso.actualizar_estado_conductor import ActualizarEstadoConductor
from app.aplicacion.casos_de_uso.obtener_estado_conductor import ObtenerEstadoConductor
from app.aplicacion.casos_de_uso.obtener_ubicacion_conductor import ObtenerUbicacionConductor
from app.dominio.conductor import EstadoConductor as EstadoConductorDominio
from app.dominio.disponibilidad import NO_INFORMADO

router = APIRouter(tags=["Disponibilidad"])


@router.get(
    "/conductores/{id_conductor}/estado",
    response_model=EstadoConductor,
    operation_id="obtenerEstadoConductor",
    dependencies=[Depends(requerir_conductor_propio_operador_o_servicio)],
)
def obtener_estado(
    id_conductor: int,
    caso: Annotated[ObtenerEstadoConductor, Depends(obtener_caso_obtener_estado_conductor)],
) -> EstadoConductor:
    return estado_desde_dominio(caso.ejecutar(id_conductor=id_conductor))


@router.patch(
    "/conductores/{id_conductor}/estado",
    response_model=EstadoConductor,
    operation_id="actualizarEstadoConductor",
    dependencies=[Depends(requerir_conductor_propio_u_operador)],
)
def actualizar_estado(
    id_conductor: int,
    datos: EstadoConductorRequest,
    caso: Annotated[ActualizarEstadoConductor, Depends(obtener_caso_actualizar_estado_conductor)],
) -> EstadoConductor:
    informa_vehiculo = "id_vehiculo_activo" in datos.model_fields_set
    resultado = caso.ejecutar(
        id_conductor=id_conductor,
        estado=EstadoConductorDominio(datos.estado.value) if datos.estado is not None else None,
        id_vehiculo_activo=datos.id_vehiculo_activo if informa_vehiculo else NO_INFORMADO,
        latitud=datos.latitud,
        longitud=datos.longitud,
    )
    return estado_desde_dominio(resultado)


@router.get(
    "/conductores/{id_conductor}/ubicacion",
    response_model=UbicacionConductor,
    operation_id="obtenerUbicacionConductor",
    dependencies=[Depends(requerir_conductor_propio_operador_o_servicio)],
)
def obtener_ubicacion(
    id_conductor: int,
    caso: Annotated[ObtenerUbicacionConductor, Depends(obtener_caso_obtener_ubicacion_conductor)],
) -> UbicacionConductor:
    return ubicacion_desde_dominio(caso.ejecutar(id_conductor=id_conductor))
