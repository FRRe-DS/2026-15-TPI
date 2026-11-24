from app.dominio.errores import NoEncontrado

from tests.ids import uid

URL = f"/api/v1/conductores/{uid(1)}"


def test_obtiene_conductor(client, casos, headers_conductor) -> None:
    respuesta = client.get(URL, headers=headers_conductor)

    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == str(uid(1))
    assert respuesta.json()["email"] == "ana@example.com"
    assert casos["obtener_conductor"].llamadas == [{"id_conductor": uid(1)}]


def test_conductor_inexistente_responde_404(client, casos, headers_operador) -> None:
    casos["obtener_conductor"].error = NoEncontrado("No existe el conductor 99")

    respuesta = client.get(f"/api/v1/conductores/{uid(99)}", headers=headers_operador)

    assert respuesta.status_code == 404
    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "NO_ENCONTRADO"
    assert cuerpo["mensaje"] == "No existe el conductor 99"


def test_un_id_que_no_es_uuid_responde_400_sin_llegar_al_caso_de_uso(
    client, casos, headers_operador
) -> None:
    for id_invalido in ("1", "no-es-un-uuid", "123e4567-e89b-12d3-a456"):
        respuesta = client.get(f"/api/v1/conductores/{id_invalido}", headers=headers_operador)

        assert respuesta.status_code == 400, id_invalido
        assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert casos["obtener_conductor"].llamadas == []
