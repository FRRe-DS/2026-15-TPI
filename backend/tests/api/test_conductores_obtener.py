from app.dominio.errores import NoEncontrado

URL = "/api/v1/conductores/1"


def test_obtiene_conductor(client, casos, headers_conductor) -> None:
    respuesta = client.get(URL, headers=headers_conductor)

    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == 1
    assert respuesta.json()["email"] == "ana@example.com"
    assert casos["obtener_conductor"].llamadas == [{"id_conductor": 1}]


def test_conductor_inexistente_responde_404(client, casos, headers_conductor) -> None:
    casos["obtener_conductor"].error = NoEncontrado("No existe el conductor 99")

    respuesta = client.get("/api/v1/conductores/99", headers=headers_conductor)

    assert respuesta.status_code == 404
    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "NO_ENCONTRADO"
    assert cuerpo["mensaje"] == "No existe el conductor 99"
