"""Endpoints del vehículo de la Iteración 2: tipos de servicio y documentación (11 y 12)."""

from __future__ import annotations

from datetime import date

import pytest
from app.aplicacion.casos_de_uso.resultados import (
    DocumentoDeVehiculo,
    DocumentoVehiculoConEstado,
    VehiculoDetalle,
)
from app.dominio.documento import EstadoDocumento
from app.dominio.documento_vehiculo import DocumentoVehiculo, TipoDocumentoVehiculo
from app.dominio.errores import DatosInvalidos, NoEncontrado
from app.dominio.vehiculo import ServicioDelVehiculo, TipoServicio
from fastapi.testclient import TestClient

from tests.api.conftest import CasoDeUsoFalso, devolver_caso, vehiculo_de_prueba

TIPOS = "/api/v1/conductores/{id}/vehiculos/5/tipos-servicio"
DOCUMENTACION = "/api/v1/conductores/{id}/vehiculos/5/documentacion"
URL_ARCHIVO = "https://archivos.example/seguro.pdf"

PAYLOAD = {
    "tipo": "SEGURO",
    "numero": "POL-1",
    "entidad_emisora": "La Segunda",
    "fecha_emision": "2026-01-01",
    "fecha_vencimiento": "2027-01-01",
    "url_archivo": URL_ARCHIVO,
}

PROVEEDORES_V5 = {
    "listar_tipos": "obtener_caso_listar_tipos_servicio_vehiculo",
    "registrar_documento": "obtener_caso_registrar_documento_vehiculo",
}


def _documento(**cambios) -> DocumentoVehiculo:
    datos = {
        "tipo": TipoDocumentoVehiculo.SEGURO,
        "numero": "POL-1",
        "entidad_emisora": "La Segunda",
        "fecha_emision": date(2026, 1, 1),
        "fecha_vencimiento": date(2027, 1, 1),
        "url_archivo": URL_ARCHIVO,
        "id": 9,
    }
    datos.update(cambios)
    return DocumentoVehiculo(**datos)


@pytest.fixture
def casos_vehiculo() -> dict[str, CasoDeUsoFalso]:
    return {
        "listar_tipos": CasoDeUsoFalso(
            [
                ServicioDelVehiculo(TipoServicio.PASAJEROS, habilitado=True),
                ServicioDelVehiculo(TipoServicio.ENVIOS, habilitado=False),
            ]
        ),
        "registrar_documento": CasoDeUsoFalso(
            DocumentoDeVehiculo(
                id_vehiculo=5, documento=_documento(), estado=EstadoDocumento.VIGENTE
            )
        ),
    }


@pytest.fixture
def client_vehiculo(client, casos_vehiculo) -> TestClient:
    from app.api import dependencias

    for clave, nombre in PROVEEDORES_V5.items():
        client.app.dependency_overrides[getattr(dependencias, nombre)] = devolver_caso(
            casos_vehiculo[clave]
        )
    return client


# --- GET tipos de servicio ----------------------------------------------------------


def test_listar_tipos_de_servicio_devuelve_la_habilitacion_de_cada_uno(
    client_vehiculo, casos_vehiculo, headers_conductor_de
) -> None:
    respuesta = client_vehiculo.get(TIPOS.format(id=1), headers=headers_conductor_de(1))

    assert respuesta.status_code == 200
    assert respuesta.json() == [
        {"tipo": "PASAJEROS", "habilitado": True},
        {"tipo": "ENVIOS", "habilitado": False},
    ]
    assert casos_vehiculo["listar_tipos"].llamadas == [{"id_conductor": 1, "id_vehiculo": 5}]


def test_listar_tipos_lo_leen_operador_servicio_y_el_propio_conductor(
    client_vehiculo, headers_operador, headers_servicio, headers_conductor_de
) -> None:
    for headers in (headers_operador, headers_servicio, headers_conductor_de(1)):
        assert client_vehiculo.get(TIPOS.format(id=1), headers=headers).status_code == 200


def test_listar_tipos_de_otro_conductor_es_403_sin_llamar_al_caso(
    client_vehiculo, casos_vehiculo, headers_conductor_de
) -> None:
    respuesta = client_vehiculo.get(TIPOS.format(id=99), headers=headers_conductor_de(1))

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "ACCESO_PROHIBIDO"
    assert casos_vehiculo["listar_tipos"].llamadas == []


def test_listar_tipos_de_un_vehiculo_inexistente_es_404(
    client_vehiculo, casos_vehiculo, headers_operador
) -> None:
    casos_vehiculo["listar_tipos"].error = NoEncontrado("No existe el vehículo 5")

    respuesta = client_vehiculo.get(TIPOS.format(id=1), headers=headers_operador)

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"


# --- POST documentación del vehículo ---------------------------------------------------


def test_registrar_documento_responde_201_con_el_estado_calculado(
    client_vehiculo, casos_vehiculo, headers_conductor_de
) -> None:
    respuesta = client_vehiculo.post(
        DOCUMENTACION.format(id=1), json=PAYLOAD, headers=headers_conductor_de(1)
    )

    assert respuesta.status_code == 201
    assert respuesta.json() == {**PAYLOAD, "id_vehiculo": 5, "estado": "VIGENTE"}
    assert casos_vehiculo["registrar_documento"].llamadas == [
        {
            "id_conductor": 1,
            "id_vehiculo": 5,
            "tipo": TipoDocumentoVehiculo.SEGURO,
            "numero": "POL-1",
            "entidad_emisora": "La Segunda",
            "fecha_emision": date(2026, 1, 1),
            "fecha_vencimiento": date(2027, 1, 1),
            "url_archivo": URL_ARCHIVO,
        }
    ]


def test_registrar_documento_sin_entidad_emisora(
    client_vehiculo, casos_vehiculo, headers_operador
) -> None:
    cuerpo = {clave: valor for clave, valor in PAYLOAD.items() if clave != "entidad_emisora"}

    respuesta = client_vehiculo.post(
        DOCUMENTACION.format(id=1), json=cuerpo, headers=headers_operador
    )

    assert respuesta.status_code == 201
    assert casos_vehiculo["registrar_documento"].llamadas[0]["entidad_emisora"] is None


@pytest.mark.parametrize(
    "cambios",
    [
        {"tipo": "LICENCIA"},
        {"url_archivo": "no-es-una-url"},
        {"url_archivo": "ftp://archivos.example/seguro.pdf"},
        {"url_archivo": "javascript:alert(1)"},
        {"url_archivo": "file:///etc/passwd"},
        {"url_archivo": "javascript://%0aalert(1)"},
        {"numero": ""},
        {"entidad_emisora": "x" * 256},
        {"fecha_emision": "ayer"},
    ],
    ids=[
        "tipo",
        "url",
        "url-ftp",
        "url-javascript",
        "url-file",
        "url-javascript-con-host",
        "numero-vacio",
        "entidad-demasiado-larga",
        "fecha",
    ],
)
def test_registrar_documento_con_cuerpo_invalido_es_400(
    client_vehiculo, casos_vehiculo, headers_operador, cambios
) -> None:
    respuesta = client_vehiculo.post(
        DOCUMENTACION.format(id=1), json={**PAYLOAD, **cambios}, headers=headers_operador
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert casos_vehiculo["registrar_documento"].llamadas == []


def test_registrar_documento_con_vencimiento_anterior_a_la_emision_es_422(
    client_vehiculo, casos_vehiculo, headers_operador
) -> None:
    casos_vehiculo["registrar_documento"].error = DatosInvalidos(
        "La fecha de vencimiento debe ser posterior a la de emisión"
    )

    respuesta = client_vehiculo.post(
        DOCUMENTACION.format(id=1),
        json={**PAYLOAD, "fecha_vencimiento": "2025-01-01"},
        headers=headers_operador,
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "DATOS_INVALIDOS"


def test_registrar_documento_de_un_vehiculo_de_otro_conductor_es_404(
    client_vehiculo, casos_vehiculo, headers_conductor_de
) -> None:
    casos_vehiculo["registrar_documento"].error = NoEncontrado(
        "No existe el vehículo 5 del conductor 1"
    )

    respuesta = client_vehiculo.post(
        DOCUMENTACION.format(id=1), json=PAYLOAD, headers=headers_conductor_de(1)
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"


def test_el_servicio_no_registra_documentos(
    client_vehiculo, casos_vehiculo, headers_servicio
) -> None:
    respuesta = client_vehiculo.post(
        DOCUMENTACION.format(id=1), json=PAYLOAD, headers=headers_servicio
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "SIN_PERMISOS"
    assert casos_vehiculo["registrar_documento"].llamadas == []


def test_registrar_documento_de_otro_conductor_es_403(
    client_vehiculo, casos_vehiculo, headers_conductor_de
) -> None:
    respuesta = client_vehiculo.post(
        DOCUMENTACION.format(id=99), json=PAYLOAD, headers=headers_conductor_de(1)
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "ACCESO_PROHIBIDO"
    assert casos_vehiculo["registrar_documento"].llamadas == []


# --- GET vehículo: documentos con su estado -------------------------------------------


def test_el_vehiculo_incluye_sus_documentos_con_estado(client, casos, headers_operador) -> None:
    casos["obtener_vehiculo"].resultado = VehiculoDetalle(
        vehiculo=vehiculo_de_prueba(),
        documentos=[
            DocumentoVehiculoConEstado(_documento(), EstadoDocumento.VIGENTE),
            DocumentoVehiculoConEstado(
                _documento(id=10, tipo=TipoDocumentoVehiculo.VTV, entidad_emisora=None),
                EstadoDocumento.VENCIDO,
            ),
        ],
    )

    respuesta = client.get("/api/v1/conductores/1/vehiculos/5", headers=headers_operador)

    assert respuesta.status_code == 200
    documentos = respuesta.json()["documentos"]
    assert [documento["tipo"] for documento in documentos] == ["SEGURO", "VTV"]
    assert [documento["estado"] for documento in documentos] == ["VIGENTE", "VENCIDO"]
    assert {documento["id_vehiculo"] for documento in documentos} == {5}
    assert documentos[0]["url_archivo"] == URL_ARCHIVO


def test_la_url_se_guarda_en_su_forma_normalizada(
    client_vehiculo, casos_vehiculo, headers_operador
) -> None:
    respuesta = client_vehiculo.post(
        DOCUMENTACION.format(id=1),
        json={**PAYLOAD, "url_archivo": "https://archivos.example"},
        headers=headers_operador,
    )

    assert respuesta.status_code == 201
    llamada = casos_vehiculo["registrar_documento"].llamadas[0]
    assert llamada["url_archivo"] == "https://archivos.example/"


def test_la_operacion_del_documento_del_vehiculo_solo_tiene_el_tag_del_contrato() -> None:
    from app.api.main import crear_app

    openapi = crear_app().openapi()
    ruta = "/api/v1/conductores/{id_conductor}/vehiculos/{id_vehiculo}/documentacion"

    assert openapi["paths"][ruta]["post"]["tags"] == ["Documentación"]
