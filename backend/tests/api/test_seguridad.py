from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Annotated, Any

import jwt
import pytest
from app.api.main import crear_app
from app.api.seguridad import obtener_cliente_jwks, requerir_operador, requerir_usuario
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

URL_COMUN = "/api/v1/comun"
URL_ACCION = "/api/v1/habilitacion"


@pytest.fixture
def client_protegido(
    cliente_jwks: SimpleNamespace,
    entorno: None,
) -> TestClient:
    """Aplicación con dos rutas de prueba protegidas por los mismos guards."""
    router = APIRouter()

    @router.get("/comun")
    def comun(
        usuario: Annotated[dict[str, Any], Depends(requerir_usuario)],
    ) -> dict[str, str]:
        return {"rol": "autorizado"}

    @router.post("/habilitacion")
    def habilitacion(
        usuario: Annotated[dict[str, Any], Depends(requerir_operador)],
    ) -> dict[str, int]:
        return {"id_operador": usuario["id_operador"]}

    app = crear_app(routers=[router])
    app.dependency_overrides[obtener_cliente_jwks] = lambda: cliente_jwks
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "token",
    [None, "esto-no-es-un-token-jwt"],
    ids=["sin-token", "token-malformado"],
)
def test_rechaza_sin_token_o_token_malformado(
    client_protegido: TestClient,
    token: str | None,
) -> None:
    headers = {} if token is None else {"Authorization": f"Bearer {token}"}

    respuesta = client_protegido.get(URL_COMUN, headers=headers)

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "NO_AUTENTICADO"


def test_rechaza_firma_invalida(
    client_protegido: TestClient,
) -> None:
    otra_clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(
        {
            "iss": "http://localhost:8080/realms/m3",
            "exp": datetime.now(UTC) + timedelta(minutes=10),
            "realm_access": {"roles": ["conductor"]},
        },
        otra_clave,
        algorithm="RS256",
        headers={"kid": "test-key-1"},
    )

    respuesta = client_protegido.get(
        URL_COMUN,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "NO_AUTENTICADO"


def test_rechaza_token_vencido(
    client_protegido: TestClient,
    crear_token,
) -> None:
    token = crear_token(
        roles=["conductor"],
        exp=datetime.now(UTC) - timedelta(minutes=1),
    )

    respuesta = client_protegido.get(
        URL_COMUN,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "NO_AUTENTICADO"


def test_rechaza_emisor_incorrecto(
    client_protegido: TestClient,
    crear_token,
) -> None:
    token = crear_token(
        roles=["conductor"],
        iss="http://emisor-incorrecto/realms/m3",
    )

    respuesta = client_protegido.get(
        URL_COMUN,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "NO_AUTENTICADO"


@pytest.mark.parametrize("roles", [["conductor"], ["operador"]])
def test_permite_roles_validos_en_endpoint_comun(
    client_protegido: TestClient,
    crear_token,
    roles: list[str],
) -> None:
    token = crear_token(roles=roles, id_operador=12 if "operador" in roles else None)

    respuesta = client_protegido.get(
        URL_COMUN,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200


@pytest.mark.parametrize(
    "roles",
    [[], ["otro-rol"]],
    ids=["sin-roles", "rol-invalido"],
)
def test_rechaza_tokens_sin_rol_autorizado(
    client_protegido: TestClient,
    crear_token,
    roles: list[str],
) -> None:
    token = crear_token(roles=roles)

    respuesta = client_protegido.get(
        URL_COMUN,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "SIN_PERMISOS"


def test_permite_token_con_rol_valido_entre_otros(
    client_protegido: TestClient,
    crear_token,
) -> None:
    token = crear_token(roles=["otro-rol", "conductor"])

    respuesta = client_protegido.get(
        URL_COMUN,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200


def test_conductor_no_puede_ejecutar_accion_de_habilitacion(
    client_protegido: TestClient,
    crear_token,
) -> None:
    token = crear_token(roles=["conductor"])

    respuesta = client_protegido.post(
        URL_ACCION,
        json={"accion": "APROBAR", "motivo": "Prueba"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "SIN_PERMISOS"


@pytest.mark.parametrize(
    "id_operador",
    [None, "no-numerico", True],
    ids=["ausente", "no-numerico", "booleano"],
)
def test_operador_sin_id_numerico_no_puede_habilitar(
    client_protegido: TestClient,
    crear_token,
    id_operador: Any,
) -> None:
    token = crear_token(roles=["operador"], id_operador=id_operador)

    respuesta = client_protegido.post(
        URL_ACCION,
        json={"accion": "APROBAR", "motivo": "Prueba"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "SIN_PERMISOS"


def test_operador_autorizado_puede_habilitar(
    client_protegido: TestClient,
    crear_token,
) -> None:
    token = crear_token(roles=["operador"], id_operador=12)

    respuesta = client_protegido.post(
        URL_ACCION,
        json={"accion": "APROBAR", "motivo": "Prueba"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"id_operador": 12}
