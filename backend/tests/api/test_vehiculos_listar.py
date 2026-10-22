from app.dominio.errores import NoEncontrado
from app.dominio.habilitacion import EstadoHabilitacion as EstadoHabilitacionDominio
from app.dominio.vehiculo import TipoVehiculo as TipoVehiculoDominio

URL = "/api/v1/conductores/1/vehiculos"


def test_lista_sin_filtros(client, casos, headers_conductor) -> None:
    respuesta = client.get(URL, headers=headers_conductor)

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1
    assert respuesta.json()[0]["id"] == 5
    assert casos["listar_vehiculos"].llamadas == [
        {"id_conductor": 1, "tipo": None, "habilitacion": None}
    ]


def test_pasa_los_filtros_al_caso_de_uso(client, casos, headers_conductor) -> None:
    respuesta = client.get(
        URL,
        params={"tipo": "MOTO", "habilitacion": "SUSPENDIDA"},
        headers=headers_conductor,
    )

    assert respuesta.status_code == 200
    assert casos["listar_vehiculos"].llamadas == [
        {
            "id_conductor": 1,
            "tipo": TipoVehiculoDominio.MOTO,
            "habilitacion": EstadoHabilitacionDominio.SUSPENDIDA,
        }
    ]


def test_tipo_invalido_responde_400(client, headers_conductor) -> None:
    respuesta = client.get(
        URL,
        params={"tipo": "AVION"},
        headers=headers_conductor,
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"


def test_conductor_inexistente_responde_404(client, casos, headers_conductor) -> None:
    casos["listar_vehiculos"].error = NoEncontrado("No existe el conductor 1")

    respuesta = client.get(URL, headers=headers_conductor)

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"
