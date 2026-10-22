from datetime import UTC, datetime

from app.aplicacion.casos_de_uso.resultados import HabilitacionResumen
from app.dominio.errores import NoEncontrado
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


def test_consulta_estado_e_historial(client, casos, headers_conductor) -> None:
    casos["consultar_habilitacion_conductor"].resultado = HabilitacionResumen(
        id_conductor=1,
        estado=EstadoHabilitacion.APROBADA,
        historial=[EVENTO],
    )

    respuesta = client.get(URL, headers=headers_conductor)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id_conductor"] == 1
    assert cuerpo["estado"] == "APROBADA"
    assert cuerpo["historial"] == [
        {
            "estado": "APROBADA",
            "motivo": "Documentación correcta",
            "id_operador": 7,
            "fecha": "2026-10-22T12:00:00Z",
        }
    ]


def test_conductor_inexistente_responde_404(client, casos, headers_conductor) -> None:
    casos["consultar_habilitacion_conductor"].error = NoEncontrado(
        "No existe el conductor 1"
    )

    respuesta = client.get(URL, headers=headers_conductor)

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"
