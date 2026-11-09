import pytest
from app.dominio.conductor import EstadoConductor
from app.dominio.vehiculo import TipoServicio as TipoServicioDominio
from app.dominio.vehiculo import TipoVehiculo as TipoVehiculoDominio

URL = "/api/v1/conductores"


def test_lista_sin_filtros(client, casos, headers_operador) -> None:
    respuesta = client.get(URL, headers=headers_operador)

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1
    assert respuesta.json()[0]["id"] == 1
    assert casos["listar_conductores"].llamadas == [
        {"habilitado": None, "estado": None, "tipo_vehiculo": None, "tipo_servicio": None}
    ]


def test_los_filtros_llegan_al_caso_de_uso(client, casos, headers_operador) -> None:
    respuesta = client.get(
        URL,
        params={
            "habilitado": "true",
            "estado": "DISPONIBLE",
            "tipo_vehiculo": "AUTO",
            "tipo_servicio": "PASAJEROS",
        },
        headers=headers_operador,
    )

    assert respuesta.status_code == 200
    assert casos["listar_conductores"].llamadas == [
        {
            "habilitado": True,
            "estado": EstadoConductor.DISPONIBLE,
            "tipo_vehiculo": TipoVehiculoDominio.AUTO,
            "tipo_servicio": TipoServicioDominio.PASAJEROS,
        }
    ]
    assert len(respuesta.json()) == 1


def test_estado_invalido_responde_400(client, headers_operador) -> None:
    respuesta = client.get(URL, params={"estado": "VOLANDO"}, headers=headers_operador)

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"


@pytest.mark.parametrize("valor", ["true", "false"])
def test_el_parametro_disponible_se_rechaza_en_lugar_de_ignorarse(
    client, casos, headers_operador, valor
) -> None:
    respuesta = client.get(URL, params={"disponible": valor}, headers=headers_operador)

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert "estado" in respuesta.json()["mensaje"]
    assert casos["listar_conductores"].llamadas == []


def test_el_parametro_disponible_no_figura_en_el_contrato_generado() -> None:
    from app.api.main import crear_app

    parametros = crear_app().openapi()["paths"]["/api/v1/conductores"]["get"]["parameters"]

    assert "disponible" not in {parametro["name"] for parametro in parametros}


def test_la_respuesta_incluye_los_campos_nuevos(client, headers_operador) -> None:
    conductor = client.get(URL, headers=headers_operador).json()[0]

    assert conductor["estado"] == "DISPONIBLE"
    assert conductor["puntaje_promedio"] is None
    assert conductor["cantidad_calificaciones"] == 0
    assert conductor["id_vehiculo_activo"] is None
    assert "conectado" not in conductor
    assert "disponible" not in conductor


def test_rechaza_tipo_vehiculo_invalido(client, headers_operador) -> None:
    respuesta = client.get(
        URL,
        params={"tipo_vehiculo": "AVION"},
        headers=headers_operador,
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"


def test_acepta_pero_descarta_la_ubicacion(client, casos, headers_operador) -> None:
    respuesta = client.get(
        URL,
        params={"latitud": "-27.45", "longitud": "-58.98"},
        headers=headers_operador,
    )

    assert respuesta.status_code == 200
    assert casos["listar_conductores"].llamadas == [
        {"habilitado": None, "estado": None, "tipo_vehiculo": None, "tipo_servicio": None}
    ]


def test_latitud_sin_longitud_responde_400(client, headers_operador) -> None:
    respuesta = client.get(
        URL,
        params={"latitud": "-27.45"},
        headers=headers_operador,
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"


def test_latitud_fuera_de_rango_responde_400(client, headers_operador) -> None:
    respuesta = client.get(
        URL,
        params={"latitud": "100", "longitud": "-58.98"},
        headers=headers_operador,
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"
