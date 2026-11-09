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
    EstadoOperativo,
    conductor_creado,
    conductor_desde_detalle,
)
from app.api.esquemas.vehiculo import TipoServicio, TipoVehiculo
from app.api.seguridad import (
    requerir_conductor_propio_operador_o_servicio,
    requerir_operador_o_conductor,
    requerir_operador_o_servicio,
)
from app.aplicacion.casos_de_uso.crear_conductor import CrearConductor
from app.aplicacion.casos_de_uso.listar_conductores import ListarConductores
from app.aplicacion.casos_de_uso.obtener_conductor import ObtenerConductor
from app.dominio.conductor import EstadoConductor
from app.dominio.vehiculo import TipoServicio as TipoServicioDominio
from app.dominio.vehiculo import TipoVehiculo as TipoVehiculoDominio

router = APIRouter(tags=["Conductores"])


@router.post(
    "/conductores",
    response_model=Conductor,
    status_code=status.HTTP_201_CREATED,
    operation_id="crearConductor",
    dependencies=[Depends(requerir_operador_o_conductor)],
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
    dependencies=[Depends(requerir_operador_o_servicio)],
)
def listar_conductores(
    caso: Annotated[ListarConductores, Depends(obtener_caso_listar_conductores)],
    habilitado: bool | None = None,
    estado: EstadoOperativo | None = None,
    tipo_vehiculo: TipoVehiculo | None = None,
    tipo_servicio: TipoServicio | None = None,
    latitud: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitud: Annotated[float | None, Query(ge=-180, le=180)] = None,
    # Solo para avisar: reemplazado por `estado` en la versión 1.2.0. Si se ignorara, un cliente sin
    # migrar recibiría a todos los conductores como si estuvieran disponibles.
    disponible: Annotated[bool | None, Query(include_in_schema=False)] = None,
) -> list[ConductorConUbicacion]:
    if disponible is not None:
        raise ErrorAPI(
            400,
            "SOLICITUD_INVALIDA",
            "El parámetro disponible se reemplazó por estado (por ejemplo, estado=DISPONIBLE)",
        )
    if (latitud is None) != (longitud is None):
        raise ErrorAPI(
            400,
            "SOLICITUD_INVALIDA",
            "latitud y longitud deben enviarse juntas",
        )

    # La ubicación se valida pero nunca filtra: el contrato la acepta y M3 no ordena por cercanía.
    conductores = caso.ejecutar(
        habilitado=habilitado,
        estado=EstadoConductor(estado.value) if estado is not None else None,
        tipo_vehiculo=(
            TipoVehiculoDominio(tipo_vehiculo.value) if tipo_vehiculo is not None else None
        ),
        tipo_servicio=(
            TipoServicioDominio(tipo_servicio.value) if tipo_servicio is not None else None
        ),
    )
    return [conductor_desde_detalle(detalle) for detalle in conductores]


@router.get(
    "/conductores/{id_conductor}",
    response_model=ConductorConUbicacion,
    operation_id="obtenerConductor",
    dependencies=[Depends(requerir_conductor_propio_operador_o_servicio)],
)
def obtener_conductor(
    id_conductor: int,
    caso: Annotated[ObtenerConductor, Depends(obtener_caso_obtener_conductor)],
) -> ConductorConUbicacion:
    return conductor_desde_detalle(caso.ejecutar(id_conductor=id_conductor))
