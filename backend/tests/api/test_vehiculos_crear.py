from app.dominio.errores import NoEncontrado, PatenteDuplicada
from app.dominio.vehiculo import TipoServicio as TipoServicioDominio
from app.dominio.vehiculo import TipoVehiculo as TipoVehiculoDominio

URL = "/api/v1/conductores/1/vehiculos"

PAYLOAD = {
    "tipo": "AUTO",
    "patente": "AB123CD",
    "marca": "Toyota",
    "modelo": "Corolla",
    "anio": 2020,
    "tipos_serv": ["PASAJEROS"],
}


def test_crea_vehiculo(client, casos, headers_conductor) -> None:
    respuesta = client.post(URL, json=PAYLOAD, headers=headers_conductor)

    assert respuesta.status_code == 201
    assert respuesta.headers["location"] == "/api/v1/conductores/1/vehiculos/5"

    cuerpo = respuesta.json()
    assert cuerpo["id"] == 5
    assert cuerpo["id_conductor"] == 1
    assert cuerpo["patente"] == "AB123CD"
    assert cuerpo["tipos_serv"] == [{"tipo": "PASAJEROS", "habilitado": False}]

    assert casos["registrar_vehiculo"].llamadas == [
        {
            "id_conductor": 1,
            "tipo": TipoVehiculoDominio.AUTO,
            "patente": "AB123CD",
            "marca": "Toyota",
            "modelo": "Corolla",
            "anio": 2020,
            "tipos_servicio": [TipoServicioDominio.PASAJEROS],
        }
    ]


def test_sin_tipos_de_servicio_responde_400(client, headers_conductor) -> None:
    respuesta = client.post(
        URL,
        json={**PAYLOAD, "tipos_serv": []},
        headers=headers_conductor,
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"


def test_conductor_inexistente_responde_404(client, casos, headers_conductor) -> None:
    casos["registrar_vehiculo"].error = NoEncontrado("No existe el conductor 1")

    respuesta = client.post(URL, json=PAYLOAD, headers=headers_conductor)

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"


def test_patente_duplicada_responde_409(client, casos, headers_conductor) -> None:
    casos["registrar_vehiculo"].error = PatenteDuplicada("La patente ya existe")

    respuesta = client.post(URL, json=PAYLOAD, headers=headers_conductor)

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "PATENTE_DUPLICADA"
