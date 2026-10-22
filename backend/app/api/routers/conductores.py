from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencias import (
    obtener_caso_crear_conductor,
    obtener_caso_listar_conductores,
    obtener_caso_obtener_conductor,
)
from app.api.errores import ErrorAPI
from app.api.esquemas.conductor import (
    Conductor,
    ConductorConUbicacion,
    ConductorCreate,
    conductor_creado,
    conductor_desde_detalle,
)
from app.api.esquemas.vehiculo import TipoServicio, TipoVehiculo
from app.aplicacion.casos_de_uso.crear_conductor import CrearConductor
from app.aplicacion.casos_de_uso.listar_conductores import ListarConductores
from app.aplicacion.casos_de_uso.obtener_conductor import ObtenerConductor
from app.dominio.vehiculo import TipoVehiculo as TipoVehiculoDominio

router = APIRouter(tags=["Conductores"])


@router.post(
    "/conductores",
    response_model=Conductor,
    status_code=status.HTTP_201_CREATED,
    operation_id="crearConductor",
)
def crear_conductor(
    datos: ConductorCreate,
    response: Response,
    caso: Annotated[CrearConductor, Depends(obtener_caso_crear_conductor)],
) -> Conductor:
    detalle = caso.ejecutar(**datos.model_dump())
    creado = conductor_creado(detalle)
    response.headers["Location"] = f"/api/v1/conductores/{creado.id}"
    return creado


@router.get(
    "/conductores",
    response_model=list[ConductorConUbicacion],
    operation_id="listarConductores",
)
def listar_conductores(
    caso: Annotated[ListarConductores, Depends(obtener_caso_listar_conductores)],
    habilitado: bool | None = None,
    disponible: bool | None = None,
    tipo_vehiculo: TipoVehiculo | None = None,
    tipo_servicio: TipoServicio | None = None,
    latitud: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitud: Annotated[float | None, Query(ge=-180, le=180)] = None,
) -> list[ConductorConUbicacion]:
    if (latitud is None) != (longitud is None):
        raise ErrorAPI(
            400,
            "SOLICITUD_INVALIDA",
            "latitud y longitud deben enviarse juntas",
        )

    # En la Iteración 1 la ubicación y el tipo de servicio se aceptan pero no
    # filtran ni ordenan; quedan para la Iteración 2.
    _ = (tipo_servicio, latitud, longitud)

    conductores = caso.ejecutar(
        habilitado=habilitado,
        disponible=disponible,
        tipo_vehiculo=(
            TipoVehiculoDominio(tipo_vehiculo.value) if tipo_vehiculo is not None else None
        ),
    )
    return [conductor_desde_detalle(detalle) for detalle in conductores]


@router.get(
    "/conductores/{id_conductor}",
    response_model=ConductorConUbicacion,
    operation_id="obtenerConductor",
)
def obtener_conductor(
    id_conductor: int,
    caso: Annotated[ObtenerConductor, Depends(obtener_caso_obtener_conductor)],
) -> ConductorConUbicacion:
    return conductor_desde_detalle(caso.ejecutar(id_conductor=id_conductor))
