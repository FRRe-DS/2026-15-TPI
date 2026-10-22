from datetime import UTC, datetime

from app.aplicacion.casos_de_uso.resultados import HabilitacionVehiculoEventos
from app.dominio.errores import NoEncontrado, TransicionInvalida
from app.dominio.habilitacion import (
    AccionHabilitacion,
    EstadoHabilitacion,
    EventoHabilitacion,
)

URL = "/api/v1/conductores/1/vehiculos/5/habilitacion"

EVENTO = EventoHabilitacion(
    accion=AccionHabilitacion.APROBAR,
    estado_anterior=EstadoHabilitacion.PENDIENTE,
    estado_nuevo=EstadoHabilitacion.APROBADA,
    motivo="Vehículo en regla",
    id_operador=7,
    fecha=datetime(2026, 10, 22, 12, 0, tzinfo=UTC),
)


def test_operador_habilita_vehiculo(client, casos, headers_operador) -> None:
    casos["accionar_habilitacion_vehiculo"].resultado = HabilitacionVehiculoEventos(
        id_vehiculo=5,
        estado=EstadoHabilitacion.APROBADA,
        eventos=[EVENTO],
    )

    respuesta = client.post(
        URL,
        json={"accion": "APROBAR", "motivo": "Vehículo en regla"},
        headers=headers_operador,
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id_vehiculo"] == 5
    assert cuerpo["estado"] == "APROBADA"
    assert cuerpo["eventos"][0]["accion"] == "APROBAR"
    assert cuerpo["eventos"][0]["id_operador"] == 7

    assert casos["accionar_habilitacion_vehiculo"].llamadas == [
        {
            "id_conductor": 1,
            "id_vehiculo": 5,
            "accion": AccionHabilitacion.APROBAR,
            "motivo": "Vehículo en regla",
            "id_operador": 7,
        }
    ]


def test_conductor_no_puede_habilitar_vehiculo(client, headers_conductor) -> None:
    respuesta = client.post(
        URL,
        json={"accion": "APROBAR", "motivo": "Prueba"},
        headers=headers_conductor,
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "SIN_PERMISOS"


def test_motivo_vacio_responde_400(client, headers_operador) -> None:
    respuesta = client.post(
        URL,
        json={"accion": "APROBAR", "motivo": ""},
        headers=headers_operador,
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"


def test_vehiculo_inexistente_responde_404(client, casos, headers_operador) -> None:
    casos["accionar_habilitacion_vehiculo"].error = NoEncontrado(
        "No existe el vehiculo 5 del conductor 1"
    )

    respuesta = client.post(
        URL,
        json={"accion": "APROBAR", "motivo": "Prueba"},
        headers=headers_operador,
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"


def test_transicion_invalida_responde_409(client, casos, headers_operador) -> None:
    casos["accionar_habilitacion_vehiculo"].error = TransicionInvalida(
        "La acción no está permitida"
    )

    respuesta = client.post(
        URL,
        json={"accion": "APROBAR", "motivo": "Prueba"},
        headers=headers_operador,
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "TRANSICION_INVALIDA"
