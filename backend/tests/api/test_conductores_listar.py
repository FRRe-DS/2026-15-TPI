from app.aplicacion.casos_de_uso.resultados import ConductorDetalle
from app.dominio.conductor import EstadoConductor
from app.dominio.vehiculo import TipoVehiculo as TipoVehiculoDominio

from tests.api.conftest import conductor_de_prueba

URL = "/api/v1/conductores"


def test_lista_sin_filtros(client, casos, headers_conductor) -> None:
    respuesta = client.get(URL, headers=headers_conductor)

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1
    assert respuesta.json()[0]["id"] == 1
    assert casos["listar_conductores"].llamadas == [
        {"habilitado": None, "estado": None, "tipo_vehiculo": None}
    ]


def test_disponible_verdadero_se_traduce_al_estado_disponible(
    client, casos, headers_conductor
) -> None:
    respuesta = client.get(
        URL,
        params={
            "habilitado": "true",
            "disponible": "true",
            "tipo_vehiculo": "AUTO",
        },
        headers=headers_conductor,
    )

    assert respuesta.status_code == 200
    assert casos["listar_conductores"].llamadas == [
        {
            "habilitado": True,
            "estado": EstadoConductor.DISPONIBLE,
            "tipo_vehiculo": TipoVehiculoDominio.AUTO,
        }
    ]
    assert len(respuesta.json()) == 1


def test_disponible_falso_excluye_a_los_conductores_disponibles(
    client, casos, headers_conductor
) -> None:
    disponible = ConductorDetalle(conductor_de_prueba(id=1), documentos=[], vehiculos=[])
    no_disponible = ConductorDetalle(
        conductor_de_prueba(id=2, estado=EstadoConductor.CONECTADO), documentos=[], vehiculos=[]
    )
    casos["listar_conductores"].resultado = [disponible, no_disponible]

    respuesta = client.get(URL, params={"disponible": "false"}, headers=headers_conductor)

    assert respuesta.status_code == 200
    assert [conductor["id"] for conductor in respuesta.json()] == [2]
    assert casos["listar_conductores"].llamadas == [
        {"habilitado": None, "estado": None, "tipo_vehiculo": None}
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
