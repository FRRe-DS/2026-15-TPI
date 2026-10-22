from app.dominio.errores import DniDuplicado

URL = "/api/v1/conductores"

PAYLOAD = {
    "dni": "12345678",
    "nombre": "Ana",
    "apellido": "Pérez",
    "telefono": "3415550000",
    "email": "ana@example.com",
}


def test_crea_conductor(client, casos, headers_conductor) -> None:
    respuesta = client.post(URL, json=PAYLOAD, headers=headers_conductor)

    assert respuesta.status_code == 201
    assert respuesta.headers["location"] == "/api/v1/conductores/1"

    cuerpo = respuesta.json()
    assert cuerpo["id"] == 1
    assert cuerpo["dni"] == PAYLOAD["dni"]
    assert cuerpo["nombre"] == PAYLOAD["nombre"]
    assert cuerpo["habilitacion"] == "APROBADA"
    assert cuerpo["documentos"] == []
    assert cuerpo["vehiculos"] == []

    assert casos["crear_conductor"].llamadas == [PAYLOAD]


def test_rechaza_dni_invalido(client, headers_conductor) -> None:
    respuesta = client.post(
        URL,
        json={**PAYLOAD, "dni": "123"},
        headers=headers_conductor,
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"


def test_dni_duplicado_responde_409(client, casos, headers_conductor) -> None:
    casos["crear_conductor"].error = DniDuplicado("El DNI ya existe")

    respuesta = client.post(URL, json=PAYLOAD, headers=headers_conductor)

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "DNI_DUPLICADO"


def test_sin_token_responde_401(client) -> None:
    respuesta = client.post(URL, json=PAYLOAD, headers={})

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "NO_AUTENTICADO"
