from datetime import date

from app.aplicacion.casos_de_uso.resultados import DocumentoDeConductor
from app.dominio.documento import EstadoDocumento
from app.dominio.errores import DatosInvalidos, NoEncontrado

from tests.api.conftest import documento_de_prueba

URL = "/api/v1/conductores/1/documentacion"

PAYLOAD = {
    "tipo": "LICENCIA",
    "numero": "LIC-1",
    "categoria": "B1",
    "fecha_emision": "2020-01-01",
    "fecha_vencimiento": "2030-01-01",
    "url_archivo": "https://archivos.example/licencia.pdf",
}


def test_registra_licencia_vigente(client, casos, headers_conductor) -> None:
    respuesta = client.post(URL, json=PAYLOAD, headers=headers_conductor)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["tipo"] == "LICENCIA"
    assert cuerpo["id_conductor"] == 1
    assert cuerpo["estado"] == "VIGENTE"
    assert cuerpo["url_archivo"] == PAYLOAD["url_archivo"]

    assert casos["registrar_licencia"].llamadas == [
        {
            "id_conductor": 1,
            "numero": "LIC-1",
            "categoria": "B1",
            "fecha_emision": date(2020, 1, 1),
            "fecha_vencimiento": date(2030, 1, 1),
            "url_archivo": PAYLOAD["url_archivo"],
        }
    ]


def test_devuelve_estado_vencido(client, casos, headers_conductor) -> None:
    casos["registrar_licencia"].resultado = DocumentoDeConductor(
        id_conductor=1,
        documento=documento_de_prueba(),
        estado=EstadoDocumento.VENCIDO,
    )

    respuesta = client.post(URL, json=PAYLOAD, headers=headers_conductor)

    assert respuesta.status_code == 201
    assert respuesta.json()["estado"] == "VENCIDO"


def test_url_invalida_responde_400(client, headers_conductor) -> None:
    respuesta = client.post(
        URL,
        json={**PAYLOAD, "url_archivo": "no-es-una-url"},
        headers=headers_conductor,
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"


def test_fecha_invalida_responde_400(client, headers_conductor) -> None:
    respuesta = client.post(
        URL,
        json={**PAYLOAD, "fecha_emision": "2020-13-01"},
        headers=headers_conductor,
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"


def test_conductor_inexistente_responde_404(client, casos, headers_conductor) -> None:
    casos["registrar_licencia"].error = NoEncontrado("No existe el conductor 1")

    respuesta = client.post(URL, json=PAYLOAD, headers=headers_conductor)

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"


def test_datos_invalidos_responde_422(client, casos, headers_conductor) -> None:
    casos["registrar_licencia"].error = DatosInvalidos(
        "La fecha de vencimiento debe ser posterior a la de emisión"
    )

    respuesta = client.post(URL, json=PAYLOAD, headers=headers_conductor)

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "DATOS_INVALIDOS"
