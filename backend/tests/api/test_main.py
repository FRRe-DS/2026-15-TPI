from types import SimpleNamespace
from typing import Annotated, Any

from app.api.main import crear_app
from app.api.seguridad import obtener_cliente_jwks, requerir_usuario
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

RUTAS_DE_DOCUMENTACION = {
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
}


def _router_protegido() -> APIRouter:
    router = APIRouter()

    @router.get("/protegido")
    def protegido(
        usuario: Annotated[dict[str, Any], Depends(requerir_usuario)],
    ) -> dict[str, bool]:
        return {"ok": True}

    return router


def test_todas_las_rutas_cuelgan_de_api_v1() -> None:
    app = crear_app(routers=[_router_protegido()])

    for camino in app.openapi()["paths"]:
        assert camino.startswith("/api/v1/"), f"Ruta fuera del prefijo: {camino}"


def test_el_prefijo_se_aplica_al_router() -> None:
    app = crear_app(routers=[_router_protegido()])

    assert "/api/v1/protegido" in app.openapi()["paths"]


def test_las_rutas_requieren_autenticacion(
    cliente_jwks: SimpleNamespace,
    entorno: None,
) -> None:
    app = crear_app(routers=[_router_protegido()])
    app.dependency_overrides[obtener_cliente_jwks] = lambda: cliente_jwks

    with TestClient(app) as client:
        respuesta = client.get("/api/v1/protegido")

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "NO_AUTENTICADO"


def test_con_token_valido_la_ruta_responde(
    cliente_jwks: SimpleNamespace,
    entorno: None,
    crear_token,
) -> None:
    app = crear_app(routers=[_router_protegido()])
    app.dependency_overrides[obtener_cliente_jwks] = lambda: cliente_jwks
    token = crear_token(roles=["conductor"])

    with TestClient(app) as client:
        respuesta = client.get(
            "/api/v1/protegido",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert respuesta.status_code == 200


def test_el_openapi_declara_bearer() -> None:
    app = crear_app(routers=[_router_protegido()])

    esquemas = app.openapi()["components"]["securitySchemes"]

    assert esquemas["HTTPBearer"]["scheme"] == "bearer"
