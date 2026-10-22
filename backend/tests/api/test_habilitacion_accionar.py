from datetime import UTC, datetime

from app.aplicacion.casos_de_uso.resultados import HabilitacionEventos
from app.dominio.errores import (
    LicenciaVigenteRequerida,
    NoEncontrado,
    TransicionInvalida,
)
from app.dominio.habilitacion import (
    AccionHabilitacion,
    EstadoHabilitacion,
    EventoHabilitacion,
)

URL = "/api/v1/conductores/1/habilitacion"

EVENTO = EventoHabilitacion(
    accion=AccionHabilitacion.APROBAR,
    estado_anterior=EstadoHabilitacion.PENDIENTE,
    estado_nuevo=EstadoHabilitacion.APROBADA,
    motivo="Documentación correcta",
    id_operador=7,
    fecha=datetime(2026, 10, 22, 12, 0, tzinfo=UTC),
)


def test_operador_aplica_la_accion(client, casos, headers_operador) -> None:
    casos["accionar_habilitacion_conductor"].resultado = HabilitacionEventos(
        id_conductor=1,
        estado=EstadoHabilitacion.APROBADA,
        eventos=[EVENTO],
    )

    respuesta = client.post(
        URL,
        json={"accion": "APROBAR", "motivo": "Documentación correcta"},
        headers=headers_operador,
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id_conductor"] == 1
    assert cuerpo["estado"] == "APROBADA"
    assert cuerpo["eventos"][0]["accion"] == "APROBAR"
    assert cuerpo["eventos"][0]["id_operador"] == 7

    assert casos["accionar_habilitacion_conductor"].llamadas == [
        {
            "id_conductor": 1,
            "accion": AccionHabilitacion.APROBAR,
            "motivo": "Documentación correcta",
            "id_operador": 7,
        }
    ]


def test_conductor_no_puede_aplicar_acciones(client, headers_conductor) -> None:
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


def test_conductor_inexistente_responde_404(client, casos, headers_operador) -> None:
    casos["accionar_habilitacion_conductor"].error = NoEncontrado(
        "No existe el conductor 1"
    )

    respuesta = client.post(
        URL,
        json={"accion": "APROBAR", "motivo": "Prueba"},
        headers=headers_operador,
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"


def test_transicion_invalida_responde_409(client, casos, headers_operador) -> None:
    casos["accionar_habilitacion_conductor"].error = TransicionInvalida(
        "La acción no está permitida"
    )

    respuesta = client.post(
        URL,
        json={"accion": "APROBAR", "motivo": "Prueba"},
        headers=headers_operador,
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "TRANSICION_INVALIDA"


def test_licencia_vencida_responde_422(client, casos, headers_operador) -> None:
    casos["accionar_habilitacion_conductor"].error = LicenciaVigenteRequerida(
        "Se requiere una licencia vigente"
    )

    respuesta = client.post(
        URL,
        json={"accion": "APROBAR", "motivo": "Prueba"},
        headers=headers_operador,
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "LICENCIA_VIGENTE_REQUERIDA"
