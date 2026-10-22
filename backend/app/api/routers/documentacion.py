from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencias import obtener_caso_registrar_licencia
from app.api.esquemas.documento import (
    DocumentoConductor,
    DocumentoConductorCreate,
    documento_desde_dominio,
)
from app.aplicacion.casos_de_uso.registrar_licencia import RegistrarLicencia

router = APIRouter(tags=["Documentación"])


@router.post(
    "/conductores/{id_conductor}/documentacion",
    response_model=DocumentoConductor,
    status_code=status.HTTP_201_CREATED,
    operation_id="crearDocumentacionConductor",
)
def registrar_documentacion(
    id_conductor: int,
    datos: DocumentoConductorCreate,
    caso: Annotated[RegistrarLicencia, Depends(obtener_caso_registrar_licencia)],
) -> DocumentoConductor:
    resultado = caso.ejecutar(
        id_conductor=id_conductor,
        numero=datos.numero,
        categoria=datos.categoria,
        fecha_emision=datos.fecha_emision,
        fecha_vencimiento=datos.fecha_vencimiento,
        url_archivo=str(datos.url_archivo),
    )
    return documento_desde_dominio(
        resultado.id_conductor,
        resultado.documento,
        resultado.estado,
    )
