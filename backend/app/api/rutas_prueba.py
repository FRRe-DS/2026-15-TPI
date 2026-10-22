
from fastapi import APIRouter, Depends

from app.api.seguridad import requerir_usuario, requerir_operador

router = APIRouter()


@router.get("/conductores")
def listar_conductores(
    usuario: dict = Depends(requerir_usuario),
):
    return []


@router.post("/conductores/1/habilitacion")
def habilitar_conductor(
    usuario: dict = Depends(requerir_operador),
):
    return {"mensaje": "Acción autorizada"}