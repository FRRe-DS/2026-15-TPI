from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencias import (
    obtener_caso_listar_vehiculos,
    obtener_caso_obtener_vehiculo,
    obtener_caso_registrar_vehiculo,
)
from app.api.esquemas.habilitacion import EstadoHabilitacion
from app.api.esquemas.vehiculo import (
    TipoVehiculo,
    Vehiculo,
    VehiculoCreate,
    VehiculoResumen,
    vehiculo_desde_dominio,
    vehiculo_resumen_desde_dominio,
)
from app.aplicacion.casos_de_uso.listar_vehiculos import ListarVehiculos
from app.aplicacion.casos_de_uso.obtener_vehiculo import ObtenerVehiculo
from app.aplicacion.casos_de_uso.registrar_vehiculo import RegistrarVehiculo
from app.dominio.habilitacion import EstadoHabilitacion as EstadoHabilitacionDominio
from app.dominio.vehiculo import TipoServicio as TipoServicioDominio
from app.dominio.vehiculo import TipoVehiculo as TipoVehiculoDominio

router = APIRouter(tags=["Vehículos"])


@router.post(
    "/conductores/{id_conductor}/vehiculos",
    response_model=Vehiculo,
    status_code=status.HTTP_201_CREATED,
    operation_id="crearVehiculo",
)
def crear_vehiculo(
    id_conductor: int,
    datos: VehiculoCreate,
    response: Response,
    caso: Annotated[RegistrarVehiculo, Depends(obtener_caso_registrar_vehiculo)],
) -> Vehiculo:
    detalle = caso.ejecutar(
        id_conductor=id_conductor,
        tipo=TipoVehiculoDominio(datos.tipo.value),
        patente=datos.patente,
        marca=datos.marca,
        modelo=datos.modelo,
        anio=datos.anio,
        tipos_servicio=[TipoServicioDominio(tipo.value) for tipo in datos.tipos_serv],
    )
    creado = vehiculo_desde_dominio(detalle.vehiculo)
    response.headers["Location"] = f"/api/v1/conductores/{id_conductor}/vehiculos/{creado.id}"
    return creado


@router.get(
    "/conductores/{id_conductor}/vehiculos",
    response_model=list[VehiculoResumen],
    operation_id="listarVehiculos",
)
def listar_vehiculos(
    id_conductor: int,
    caso: Annotated[ListarVehiculos, Depends(obtener_caso_listar_vehiculos)],
    tipo: TipoVehiculo | None = None,
    habilitacion: EstadoHabilitacion | None = None,
) -> list[VehiculoResumen]:
    vehiculos = caso.ejecutar(
        id_conductor=id_conductor,
        tipo=TipoVehiculoDominio(tipo.value) if tipo is not None else None,
        habilitacion=(
            EstadoHabilitacionDominio(habilitacion.value) if habilitacion is not None else None
        ),
    )
    return [vehiculo_resumen_desde_dominio(vehiculo) for vehiculo in vehiculos]


@router.get(
    "/conductores/{id_conductor}/vehiculos/{id_vehiculo}",
    response_model=Vehiculo,
    operation_id="obtenerVehiculo",
)
def obtener_vehiculo(
    id_conductor: int,
    id_vehiculo: int,
    caso: Annotated[ObtenerVehiculo, Depends(obtener_caso_obtener_vehiculo)],
) -> Vehiculo:
    detalle = caso.ejecutar(id_conductor=id_conductor, id_vehiculo=id_vehiculo)
    return vehiculo_desde_dominio(detalle.vehiculo)
