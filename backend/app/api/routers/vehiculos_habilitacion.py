from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.dependencias import obtener_caso_accionar_habilitacion_vehiculo
from app.api.esquemas.habilitacion import (
    HabilitacionAccionRequest,
    HabilitacionVehiculoEventos,
    eventos_vehiculo_desde_dominio,
)
from app.api.seguridad import requerir_operador
from app.aplicacion.casos_de_uso.accionar_habilitacion_vehiculo import (
    AccionarHabilitacionVehiculo,
)
from app.dominio.habilitacion import AccionHabilitacion

router = APIRouter(tags=["Habilitación"])


@router.post(
    "/conductores/{id_conductor}/vehiculos/{id_vehiculo}/habilitacion",
    response_model=HabilitacionVehiculoEventos,
    operation_id="accionHabilitacionVehiculo",
)
def accionar_habilitacion(
    id_conductor: int,
    id_vehiculo: int,
    datos: HabilitacionAccionRequest,
    caso: Annotated[
        AccionarHabilitacionVehiculo,
        Depends(obtener_caso_accionar_habilitacion_vehiculo),
    ],
    usuario: Annotated[dict[str, Any], Depends(requerir_operador)],
) -> HabilitacionVehiculoEventos:
    resultado = caso.ejecutar(
        id_conductor=id_conductor,
        id_vehiculo=id_vehiculo,
        accion=AccionHabilitacion(datos.accion.value),
        motivo=datos.motivo,
        id_operador=usuario["id_operador"],
    )
    return eventos_vehiculo_desde_dominio(resultado)
