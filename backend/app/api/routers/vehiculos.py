from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencias import (
    obtener_caso_listar_tipos_servicio_vehiculo,
    obtener_caso_listar_vehiculos,
    obtener_caso_obtener_vehiculo,
    obtener_caso_registrar_documento_vehiculo,
    obtener_caso_registrar_vehiculo,
)
from app.api.esquemas.documento import (
    DocumentoVehiculo,
    DocumentoVehiculoCreate,
    documento_vehiculo_desde_dominio,
)
from app.api.esquemas.habilitacion import EstadoHabilitacion
from app.api.esquemas.vehiculo import (
    TipoServicioHabilitado,
    TipoVehiculo,
    Vehiculo,
    VehiculoCreate,
    VehiculoResumen,
    servicios_desde_dominio,
    vehiculo_desde_dominio,
    vehiculo_resumen_desde_dominio,
)
from app.api.seguridad import (
    requerir_conductor_propio_operador_o_servicio,
    requerir_conductor_propio_u_operador,
)
from app.aplicacion.casos_de_uso.listar_tipos_servicio_vehiculo import (
    ListarTiposServicioVehiculo,
)
from app.aplicacion.casos_de_uso.listar_vehiculos import ListarVehiculos
from app.aplicacion.casos_de_uso.obtener_vehiculo import ObtenerVehiculo
from app.aplicacion.casos_de_uso.registrar_documento_vehiculo import (
    RegistrarDocumentoVehiculo,
)
from app.aplicacion.casos_de_uso.registrar_vehiculo import RegistrarVehiculo
from app.dominio.documento_vehiculo import TipoDocumentoVehiculo as TipoDocumentoVehiculoDominio
from app.dominio.habilitacion import EstadoHabilitacion as EstadoHabilitacionDominio
from app.dominio.vehiculo import TipoServicio as TipoServicioDominio
from app.dominio.vehiculo import TipoVehiculo as TipoVehiculoDominio

router = APIRouter()


@router.post(
    "/conductores/{id_conductor}/vehiculos",
    response_model=Vehiculo,
    status_code=status.HTTP_201_CREATED,
    operation_id="crearVehiculo",
    tags=["Vehículos"],
    dependencies=[Depends(requerir_conductor_propio_u_operador)],
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
    tags=["Vehículos"],
    dependencies=[Depends(requerir_conductor_propio_operador_o_servicio)],
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
    tags=["Vehículos"],
    dependencies=[Depends(requerir_conductor_propio_operador_o_servicio)],
)
def obtener_vehiculo(
    id_conductor: int,
    id_vehiculo: int,
    caso: Annotated[ObtenerVehiculo, Depends(obtener_caso_obtener_vehiculo)],
) -> Vehiculo:
    detalle = caso.ejecutar(id_conductor=id_conductor, id_vehiculo=id_vehiculo)
    return vehiculo_desde_dominio(detalle.vehiculo, detalle.documentos)


@router.get(
    "/conductores/{id_conductor}/vehiculos/{id_vehiculo}/tipos-servicio",
    response_model=list[TipoServicioHabilitado],
    operation_id="listarTiposServicioVehiculo",
    tags=["Vehículos"],
    dependencies=[Depends(requerir_conductor_propio_operador_o_servicio)],
)
def listar_tipos_servicio(
    id_conductor: int,
    id_vehiculo: int,
    caso: Annotated[
        ListarTiposServicioVehiculo, Depends(obtener_caso_listar_tipos_servicio_vehiculo)
    ],
) -> list[TipoServicioHabilitado]:
    servicios = caso.ejecutar(id_conductor=id_conductor, id_vehiculo=id_vehiculo)
    return servicios_desde_dominio(servicios)


@router.post(
    "/conductores/{id_conductor}/vehiculos/{id_vehiculo}/documentacion",
    response_model=DocumentoVehiculo,
    status_code=status.HTTP_201_CREATED,
    operation_id="crearDocumentacionVehiculo",
    tags=["Documentación"],
    dependencies=[Depends(requerir_conductor_propio_u_operador)],
)
def registrar_documentacion_vehiculo(
    id_conductor: int,
    id_vehiculo: int,
    datos: DocumentoVehiculoCreate,
    caso: Annotated[RegistrarDocumentoVehiculo, Depends(obtener_caso_registrar_documento_vehiculo)],
) -> DocumentoVehiculo:
    resultado = caso.ejecutar(
        id_conductor=id_conductor,
        id_vehiculo=id_vehiculo,
        tipo=TipoDocumentoVehiculoDominio(datos.tipo.value),
        numero=datos.numero,
        entidad_emisora=datos.entidad_emisora,
        fecha_emision=datos.fecha_emision,
        fecha_vencimiento=datos.fecha_vencimiento,
        url_archivo=str(datos.url_archivo),
    )
    return documento_vehiculo_desde_dominio(
        resultado.id_vehiculo, resultado.documento, resultado.estado
    )
