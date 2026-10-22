from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.dependencias import (
    obtener_caso_accionar_habilitacion_conductor,
    obtener_caso_consultar_habilitacion_conductor,
)
from app.api.esquemas.habilitacion import (
    HabilitacionAccionRequest,
    HabilitacionEventos,
    HabilitacionResumen,
    eventos_conductor_desde_dominio,
    resumen_desde_dominio,
)
from app.api.seguridad import requerir_operador
from app.aplicacion.casos_de_uso.accionar_habilitacion_conductor import (
    AccionarHabilitacionConductor,
)
from app.aplicacion.casos_de_uso.consultar_habilitacion_conductor import (
    ConsultarHabilitacionConductor,
)
from app.dominio.habilitacion import AccionHabilitacion

router = APIRouter(tags=["Habilitación"])


@router.get(
    "/conductores/{id_conductor}/habilitacion",
    response_model=HabilitacionResumen,
    operation_id="obtenerHabilitacionConductor",
)
def consultar_habilitacion(
    id_conductor: int,
    caso: Annotated[
        ConsultarHabilitacionConductor,
        Depends(obtener_caso_consultar_habilitacion_conductor),
    ],
) -> HabilitacionResumen:
    return resumen_desde_dominio(caso.ejecutar(id_conductor=id_conductor))


@router.post(
    "/conductores/{id_conductor}/habilitacion",
    response_model=HabilitacionEventos,
    operation_id="accionHabilitacionConductor",
)
def accionar_habilitacion(
    id_conductor: int,
    datos: HabilitacionAccionRequest,
    caso: Annotated[
        AccionarHabilitacionConductor,
        Depends(obtener_caso_accionar_habilitacion_conductor),
    ],
    usuario: Annotated[dict[str, Any], Depends(requerir_operador)],
) -> HabilitacionEventos:
    resultado = caso.ejecutar(
        id_conductor=id_conductor,
        accion=AccionHabilitacion(datos.accion.value),
        motivo=datos.motivo,
        id_operador=usuario["id_operador"],
    )
    return eventos_conductor_desde_dominio(resultado)
