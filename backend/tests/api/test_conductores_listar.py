from app.dominio.vehiculo import TipoVehiculo as TipoVehiculoDominio

URL = "/api/v1/conductores"


def test_lista_sin_filtros(client, casos, headers_conductor) -> None:
    respuesta = client.get(URL, headers=headers_conductor)

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1
    assert respuesta.json()[0]["id"] == 1
    assert casos["listar_conductores"].llamadas == [
        {"habilitado": None, "disponible": None, "tipo_vehiculo": None}
    ]


def test_pasa_los_filtros_al_caso_de_uso(client, casos, headers_conductor) -> None:
    respuesta = client.get(
        URL,
        params={
            "habilitado": "true",
            "disponible": "false",
            "tipo_vehiculo": "AUTO",
        },
        headers=headers_conductor,
    )

    assert respuesta.status_code == 200
    assert casos["listar_conductores"].llamadas == [
        {
            "habilitado": True,
            "disponible": False,
            "tipo_vehiculo": TipoVehiculoDominio.AUTO,
        }
    ]


def test_rechaza_tipo_vehiculo_invalido(client, headers_conductor) -> None:
    respuesta = client.get(
        URL,
        params={"tipo_vehiculo": "AVION"},
        headers=headers_conductor,
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"


def test_acepta_e_ignora_ubicacion_y_tipo_servicio(
    client,
    casos,
    headers_conductor,
) -> None:
    respuesta = client.get(
        URL,
        params={
            "latitud": "-27.45",
            "longitud": "-58.98",
            "tipo_servicio": "PASAJEROS",
        },
        headers=headers_conductor,
    )

    assert respuesta.status_code == 200
    assert casos["listar_conductores"].llamadas[0]["tipo_vehiculo"] is None


def test_latitud_sin_longitud_responde_400(client, headers_conductor) -> None:
    respuesta = client.get(
        URL,
        params={"latitud": "-27.45"},
        headers=headers_conductor,
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"


def test_latitud_fuera_de_rango_responde_400(client, headers_conductor) -> None:
    respuesta = client.get(
        URL,
        params={"latitud": "100", "longitud": "-58.98"},
        headers=headers_conductor,
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"
