
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa


URL_CONDUCTORES = "/api/v1/conductores"
URL_HABILITACION = "/api/v1/conductores/1/habilitacion"
EMISOR_VALIDO = "http://localhost:8080/realms/m3"


@pytest.mark.parametrize(
    "token",
    [
        None,
        "esto-no-es-un-token-jwt",
    ],
    ids=["sin-token", "token-malformado"],
)
def test_rechaza_sin_token_o_token_malformado(client, token):
    headers = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    response = client.get(URL_CONDUCTORES, headers=headers)

    assert response.status_code == 401


def test_rechaza_firma_invalida(client, crear_token):
    otra_clave = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    token = jwt.encode(
        {
            "iss": EMISOR_VALIDO,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
            "realm_access": {"roles": ["conductor"]},
        },
        otra_clave,
        algorithm="RS256",
        headers={"kid": "test-key-1"},
    )

    response = client.get(
        URL_CONDUCTORES,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_rechaza_token_vencido(client, crear_token):
    token = crear_token(
        roles=["conductor"],
        exp=datetime.now(timezone.utc) - timedelta(minutes=1),
        iss=EMISOR_VALIDO,
    )

    response = client.get(
        URL_CONDUCTORES,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_rechaza_emisor_incorrecto(client, crear_token):
    token = crear_token(
        roles=["conductor"],
        iss="http://emisor-incorrecto/realms/m3",
    )

    response = client.get(
        URL_CONDUCTORES,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    "roles",
    [
        ["conductor"],
        ["operador"],
    ],
    ids=["conductor", "operador"],
)
def test_permite_roles_validos_en_endpoint_comun(
    client,
    crear_token,
    roles,
):
    token = crear_token(
        roles=roles,
        id_operador=12 if "operador" in roles else None,
        iss=EMISOR_VALIDO,
    )

    response = client.get(
        URL_CONDUCTORES,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_conductor_no_puede_ejecutar_habilitacion(client, crear_token):
    token = crear_token(
        roles=["conductor"],
        iss=EMISOR_VALIDO,
    )

    response = client.post(
        URL_HABILITACION,
        json={"accion": "APROBAR", "motivo": "Prueba de seguridad"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    "id_operador",
    [None, "no-numerico"],
    ids=["id-operador-ausente", "id-operador-no-numerico"],
)
def test_operador_sin_id_numerico_no_puede_habilitar(
    client,
    crear_token,
    id_operador,
):
    token = crear_token(
        roles=["operador"],
        id_operador=id_operador,
        iss=EMISOR_VALIDO,
    )

    response = client.post(
        URL_HABILITACION,
        json={"accion": "APROBAR", "motivo": "Prueba de seguridad"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403