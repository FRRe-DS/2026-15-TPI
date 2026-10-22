from app.dominio.errores import NoEncontrado

URL = "/api/v1/conductores/1/vehiculos/5"


def test_obtiene_vehiculo(client, casos, headers_conductor) -> None:
    respuesta = client.get(URL, headers=headers_conductor)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id"] == 5
    assert cuerpo["id_conductor"] == 1
    assert cuerpo["patente"] == "AB123CD"
    assert casos["obtener_vehiculo"].llamadas == [{"id_conductor": 1, "id_vehiculo": 5}]


def test_vehiculo_inexistente_o_de_otro_conductor_responde_404(
    client,
    casos,
    headers_conductor,
) -> None:
    casos["obtener_vehiculo"].error = NoEncontrado("No existe el vehiculo 5 del conductor 1")

    respuesta = client.get(URL, headers=headers_conductor)

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"
