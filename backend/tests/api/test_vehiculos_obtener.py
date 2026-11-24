from app.dominio.errores import NoEncontrado

from tests.ids import uid

URL = f"/api/v1/conductores/{uid(1)}/vehiculos/{uid(5)}"


def test_obtiene_vehiculo(client, casos, headers_conductor) -> None:
    respuesta = client.get(URL, headers=headers_conductor)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id"] == str(uid(5))
    assert cuerpo["id_conductor"] == str(uid(1))
    assert cuerpo["patente"] == "AB123CD"
    assert casos["obtener_vehiculo"].llamadas == [{"id_conductor": uid(1), "id_vehiculo": uid(5)}]


def test_vehiculo_inexistente_o_de_otro_conductor_responde_404(
    client,
    casos,
    headers_conductor,
) -> None:
    casos["obtener_vehiculo"].error = NoEncontrado("No existe el vehiculo 5 del conductor 1")

    respuesta = client.get(URL, headers=headers_conductor)

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"
