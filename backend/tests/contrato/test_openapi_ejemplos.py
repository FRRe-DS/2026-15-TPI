"""T611: ejemplos y consistencia del contrato en las 17 operaciones del alcance."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

RAIZ_REPO = Path(__file__).resolve().parents[3]
RUTA_CONTRATO = RAIZ_REPO / "docs" / "contract" / "openapi.yaml"

# Las 17 operaciones del alcance de la Iteración 2 (spec.md, US5).
OPERACIONES_EN_ALCANCE = [
    ("post", "/conductores"),
    ("get", "/conductores"),
    ("get", "/conductores/{id_conductor}"),
    ("get", "/conductores/{id_conductor}/habilitacion"),
    ("post", "/conductores/{id_conductor}/habilitacion"),
    ("post", "/conductores/{id_conductor}/documentacion"),
    ("post", "/conductores/{id_conductor}/vehiculos"),
    ("get", "/conductores/{id_conductor}/vehiculos"),
    ("get", "/conductores/{id_conductor}/vehiculos/{id_vehiculo}"),
    (
        "post",
        "/conductores/{id_conductor}/vehiculos/{id_vehiculo}/habilitacion",
    ),
    ("get", "/conductores/{id_conductor}/vehiculos/{id_vehiculo}/tipos-servicio"),
    ("post", "/conductores/{id_conductor}/vehiculos/{id_vehiculo}/documentacion"),
    ("get", "/conductores/{id_conductor}/estado"),
    ("patch", "/conductores/{id_conductor}/estado"),
    ("get", "/conductores/{id_conductor}/ubicacion"),
    ("get", "/conductores/{id_conductor}/solicitudes"),
    ("post", "/solicitudes/{id_solicitud}"),
]

IDS_OPERACIONES = [f"{metodo.upper()} {ruta}" for metodo, ruta in OPERACIONES_EN_ALCANCE]

# Respuestas de error que T611 exige que tengan ejemplo.
ERRORES_OBLIGATORIOS = ("400", "401", "403", "404", "409", "410", "422", "429", "503")

# Códigos del catálogo (specs/iteracion1/contracts/errores.md) válidos por estado.
CODIGOS_POR_ESTADO = {
    "400": {"SOLICITUD_INVALIDA"},
    "401": {"NO_AUTENTICADO"},
    "403": {"SIN_PERMISOS"},
    "404": {"NO_ENCONTRADO"},
    "409": {
        "DNI_DUPLICADO",
        "PATENTE_DUPLICADA",
        "TRANSICION_INVALIDA",
        "SOLICITUD_YA_RESPONDIDA",
    },
    "410": {"SOLICITUD_VENCIDA"},
    "422": {
        "DATOS_INVALIDOS",
        "LICENCIA_VIGENTE_REQUERIDA",
        "CONDUCTOR_NO_HABILITADO",
    },
    "429": {"LIMITE_DE_SOLICITUDES"},
    "503": {"SERVICIO_TEMPORALMENTE_NO_DISPONIBLE"},
}

PATRON_OPERATION_ID = re.compile(r"^[a-z][a-zA-Z0-9]*$")
PATRON_ESQUEMA = re.compile(r"^[A-Z][A-Za-z0-9]*$")
PATRON_PROPIEDAD = re.compile(r"^[a-z][a-z0-9_]*$")
PATRON_SEGMENTO = re.compile(r"^[a-z0-9_.~{}-]+$")


@pytest.fixture(scope="module")
def contrato() -> dict[str, Any]:
    with RUTA_CONTRATO.open(encoding="utf-8") as archivo:
        return yaml.safe_load(archivo)


def test_el_alcance_contractual_contiene_las_17_operaciones_unicas(
    contrato: dict[str, Any],
) -> None:
    assert len(OPERACIONES_EN_ALCANCE) == 17
    assert len(set(OPERACIONES_EN_ALCANCE)) == 17
    for metodo, ruta in OPERACIONES_EN_ALCANCE:
        assert metodo in contrato["paths"].get(ruta, {}), (
            f"Falta {metodo.upper()} {ruta} en el contrato OpenAPI"
        )


def test_operaciones_autenticadas_documentan_respuestas_de_limitacion(
    contrato: dict[str, Any],
) -> None:
    for metodo, ruta in OPERACIONES_EN_ALCANCE:
        operacion = contrato["paths"][ruta][metodo]
        seguridad = operacion.get("security", contrato.get("security", []))
        if not seguridad:
            continue

        respuestas = operacion["responses"]
        assert "429" in respuestas, (
            f"{metodo.upper()} {ruta} debe documentar 429 LIMITE_DE_SOLICITUDES"
        )
        assert "503" in respuestas, (
            f"{metodo.upper()} {ruta} debe documentar 503 SERVICIO_TEMPORALMENTE_NO_DISPONIBLE"
        )
        respuesta_429 = _resolver(contrato, respuestas["429"])
        assert "Retry-After" in respuesta_429.get("headers", {}), (
            f"{metodo.upper()} {ruta} debe documentar el encabezado Retry-After en 429"
        )
        assert "Cache-Control" in respuesta_429["headers"], (
            f"{metodo.upper()} {ruta} debe documentar Cache-Control en 429"
        )


def test_retry_after_es_entero_en_segundos(contrato: dict[str, Any]) -> None:
    respuesta = _resolver(contrato, contrato["components"]["responses"]["TooManyRequests"])
    encabezado = _resolver(contrato, respuesta["headers"]["Retry-After"])

    assert encabezado["schema"]["type"] == "string"
    assert "segundos enteros" in encabezado["description"].casefold()
    cache_control = _resolver(contrato, respuesta["headers"]["Cache-Control"])
    assert cache_control["schema"]["enum"] == ["no-store"]


def _resolver(contrato: dict[str, Any], nodo: dict[str, Any]) -> dict[str, Any]:
    """Sigue los `$ref` internos hasta el nodo real."""
    vistos: set[str] = set()
    while isinstance(nodo, dict) and "$ref" in nodo:
        referencia = nodo["$ref"]
        assert referencia.startswith("#/"), f"$ref externo no soportado: {referencia}"
        assert referencia not in vistos, f"$ref circular: {referencia}"
        vistos.add(referencia)
        nodo = contrato
        for parte in referencia.removeprefix("#/").split("/"):
            nodo = nodo[parte]
    return nodo


def _ejemplos(contrato: dict[str, Any], contenido: dict[str, Any] | None) -> list[Any]:
    """Devuelve los ejemplos de un `content`, vengan del media type o del schema."""
    medio = (contenido or {}).get("application/json")
    if not medio:
        return []
    if "example" in medio:
        return [medio["example"]]
    if "examples" in medio:
        return [ejemplo["value"] for ejemplo in medio["examples"].values() if "value" in ejemplo]
    esquema = _resolver(contrato, medio.get("schema", {}))
    if "example" in esquema:
        return [esquema["example"]]
    if "examples" in esquema:
        return list(esquema["examples"])
    return []


def _tiene_acentos(texto: str) -> bool:
    return any(unicodedata.combining(caracter) for caracter in unicodedata.normalize("NFKD", texto))


def _esquemas_del_alcance(contrato: dict[str, Any]) -> set[str]:
    """Nombres de los esquemas alcanzables desde las 17 operaciones."""
    nombres: set[str] = set()

    def visitar(nodo: Any) -> None:
        if isinstance(nodo, dict):
            referencia = nodo.get("$ref")
            if isinstance(referencia, str):
                prefijo = "#/components/schemas/"
                if referencia.startswith(prefijo):
                    nombre = referencia.removeprefix(prefijo)
                    if nombre not in nombres:
                        nombres.add(nombre)
                        visitar(_resolver(contrato, nodo))
                return
            for valor in nodo.values():
                visitar(valor)
        elif isinstance(nodo, list):
            for valor in nodo:
                visitar(valor)

    for metodo, ruta in OPERACIONES_EN_ALCANCE:
        visitar(contrato["paths"][ruta][metodo])
    return nombres


@pytest.mark.parametrize(("metodo", "ruta"), OPERACIONES_EN_ALCANCE, ids=IDS_OPERACIONES)
def test_cada_cuerpo_de_peticion_tiene_ejemplo(
    contrato: dict[str, Any], metodo: str, ruta: str
) -> None:
    operacion = contrato["paths"][ruta][metodo]
    cuerpo = operacion.get("requestBody")
    if cuerpo is None:
        return  # La operación no recibe cuerpo.
    ejemplos = _ejemplos(contrato, cuerpo.get("content"))
    assert ejemplos, f"{metodo.upper()} {ruta} no tiene example en el requestBody"


@pytest.mark.parametrize(("metodo", "ruta"), OPERACIONES_EN_ALCANCE, ids=IDS_OPERACIONES)
def test_cada_respuesta_2xx_tiene_ejemplo(contrato: dict[str, Any], metodo: str, ruta: str) -> None:
    respuestas = contrato["paths"][ruta][metodo]["responses"]
    exitosas = [codigo for codigo in respuestas if codigo.startswith("2")]
    assert exitosas, f"{metodo.upper()} {ruta} no declara una respuesta 2xx"
    for codigo in exitosas:
        respuesta = _resolver(contrato, respuestas[codigo])
        assert _ejemplos(contrato, respuesta.get("content")), (
            f"{metodo.upper()} {ruta} no tiene example en la respuesta {codigo}"
        )


@pytest.mark.parametrize(("metodo", "ruta"), OPERACIONES_EN_ALCANCE, ids=IDS_OPERACIONES)
def test_cada_respuesta_de_error_tiene_ejemplo_del_catalogo(
    contrato: dict[str, Any], metodo: str, ruta: str
) -> None:
    respuestas = contrato["paths"][ruta][metodo]["responses"]
    declarados = [codigo for codigo in ERRORES_OBLIGATORIOS if codigo in respuestas]
    for codigo in declarados:
        respuesta = _resolver(contrato, respuestas[codigo])
        ejemplos = _ejemplos(contrato, respuesta.get("content"))
        assert ejemplos, f"{metodo.upper()} {ruta} no tiene example en la respuesta {codigo}"
        for ejemplo in ejemplos:
            assert isinstance(ejemplo, dict), (
                f"El example de {codigo} en {metodo.upper()} {ruta} debe ser un objeto"
            )
            assert {"codigo", "mensaje"} <= ejemplo.keys(), (
                f"El example de {codigo} en {metodo.upper()} {ruta} debe tener codigo y mensaje"
            )
            assert isinstance(ejemplo["mensaje"], str) and ejemplo["mensaje"], (
                f"El mensaje del example de {codigo} en {metodo.upper()} {ruta} "
                "no puede estar vacío"
            )
            assert ejemplo["codigo"] in CODIGOS_POR_ESTADO[codigo], (
                f"El código {ejemplo['codigo']!r} del example de {codigo} "
                f"en {metodo.upper()} {ruta} no corresponde al catálogo "
                f"para ese estado"
            )


def test_rutas_consistentes() -> None:
    for _, ruta in OPERACIONES_EN_ALCANCE:
        assert ruta.startswith("/"), f"La ruta {ruta} debe empezar con /"
        assert not ruta.endswith("/"), f"La ruta {ruta} no debe terminar con /"
        assert " " not in ruta, f"La ruta {ruta} no debe tener espacios"
        assert not _tiene_acentos(ruta), f"La ruta {ruta} no debe tener tildes"
        assert ruta == ruta.lower(), f"La ruta {ruta} debe estar en minúsculas"

        segmentos = ruta.strip("/").split("/")
        for segmento in segmentos:
            assert PATRON_SEGMENTO.fullmatch(segmento), f"Segmento inválido en {ruta}: {segmento!r}"
        assert segmentos[0].endswith("s"), f"El recurso base de {ruta} debe ir en plural"


def test_operation_ids_consistentes_y_unicos(contrato: dict[str, Any]) -> None:
    operation_ids: list[str] = []
    for metodo, ruta in OPERACIONES_EN_ALCANCE:
        operation_id = contrato["paths"][ruta][metodo]["operationId"]
        assert PATRON_OPERATION_ID.fullmatch(operation_id), (
            f"operationId inválido en {metodo.upper()} {ruta}: {operation_id!r}"
        )
        assert not _tiene_acentos(operation_id), (
            f"operationId con tildes en {metodo.upper()} {ruta}: {operation_id!r}"
        )
        operation_ids.append(operation_id)
    assert len(operation_ids) == len(set(operation_ids)), (
        "Hay operationId duplicados entre las operaciones del alcance"
    )


def test_nombres_de_esquemas_y_propiedades_consistentes(
    contrato: dict[str, Any],
) -> None:
    for nombre in _esquemas_del_alcance(contrato):
        assert PATRON_ESQUEMA.fullmatch(nombre), f"Nombre de esquema inválido: {nombre!r}"
        assert not _tiene_acentos(nombre), f"Esquema con tildes: {nombre!r}"

        esquema = _resolver(contrato, {"$ref": f"#/components/schemas/{nombre}"})
        for propiedad in esquema.get("properties", {}):
            assert PATRON_PROPIEDAD.fullmatch(propiedad), (
                f"Propiedad inválida en {nombre}: {propiedad!r}"
            )
            assert not _tiene_acentos(propiedad), f"Propiedad con tildes en {nombre}: {propiedad!r}"


def test_estado_anterior_admite_null_en_evento_de_alta(contrato):
    from openapi_schema_validator import OAS30Validator

    esquema = contrato["components"]["schemas"]["HabilitacionEvento"]["properties"][
        "estado_anterior"
    ]
    OAS30Validator(esquema).validate(None)


def _insertar_solicitud(engine: Engine, id_conductor: int, *, vence_en: datetime) -> int:
    """Inserta una solicitud pendiente; M6 no forma parte de este contrato."""
    with engine.begin() as conexion:
        return conexion.execute(
            text(
                "INSERT INTO solicitud (id_conductor, id_viaje, estado, vence_en) "
                "VALUES (:id_conductor, :id_viaje, 'PENDIENTE', :vence_en) "
                "RETURNING id_solicitud"
            ),
            {"id_conductor": id_conductor, "id_viaje": 5521, "vence_en": vence_en},
        ).scalar_one()


@pytest.mark.integration
def test_respuestas_reales_de_los_7_endpoints_nuevos_cumplen_el_contrato(
    cliente: TestClient,
    headers_conductor: dict[str, str],
    headers_conductor_de: Callable[[int], dict[str, str]],
    crear_conductor: Callable[..., dict[str, Any]],
    crear_vehiculo: Callable[..., httpx.Response],
    engine_contrato: Engine,
    validar_contrato: Callable[[httpx.Response], None],
) -> None:
    conductor = crear_conductor()
    id_conductor = conductor["id"]
    respuesta_vehiculo = crear_vehiculo(id_conductor)
    assert respuesta_vehiculo.status_code == 201, respuesta_vehiculo.text
    id_vehiculo = respuesta_vehiculo.json()["id"]

    fecha_actual = datetime.now(UTC).date()
    documento_vehiculo = {
        "tipo": "SEGURO",
        "numero": "POL-625000",
        "entidad_emisora": "Aseguradora de prueba",
        "fecha_emision": (fecha_actual - timedelta(days=30)).isoformat(),
        "fecha_vencimiento": (fecha_actual + timedelta(days=365)).isoformat(),
        "url_archivo": "https://storage.example.com/vehiculos/seguro.pdf",
    }

    respuestas: list[tuple[httpx.Response, int]] = [
        (
            cliente.get(
                f"/api/v1/conductores/{id_conductor}/vehiculos/{id_vehiculo}/tipos-servicio",
                headers=headers_conductor,
            ),
            200,
        ),
        (
            cliente.post(
                f"/api/v1/conductores/{id_conductor}/vehiculos/{id_vehiculo}/documentacion",
                json=documento_vehiculo,
                headers=headers_conductor,
            ),
            201,
        ),
        (
            cliente.get(
                f"/api/v1/conductores/{id_conductor}/estado",
                headers=headers_conductor,
            ),
            200,
        ),
        (
            cliente.patch(
                f"/api/v1/conductores/{id_conductor}/estado",
                json={"estado": "CONECTADO"},
                headers=headers_conductor,
            ),
            200,
        ),
        (
            cliente.get(
                f"/api/v1/conductores/{id_conductor}/ubicacion",
                headers=headers_conductor,
            ),
            200,
        ),
        (
            cliente.get(
                f"/api/v1/conductores/{id_conductor}/solicitudes",
                headers=headers_conductor,
            ),
            200,
        ),
    ]
    for respuesta, estado_esperado in respuestas:
        assert respuesta.status_code == estado_esperado, respuesta.text
        validar_contrato(respuesta)

    id_solicitud = _insertar_solicitud(
        engine_contrato,
        id_conductor,
        vence_en=datetime.now(UTC) + timedelta(hours=1),
    )
    listado = cliente.get(
        f"/api/v1/conductores/{id_conductor}/solicitudes",
        headers=headers_conductor,
    )
    assert listado.status_code == 200, listado.text
    validar_contrato(listado)
    assert [solicitud["id"] for solicitud in listado.json()] == [id_solicitud]

    respuesta_solicitud = cliente.post(
        f"/api/v1/solicitudes/{id_solicitud}",
        json={
            "respuesta": "RECHAZADO",
            "hora_rta": datetime.now(UTC).isoformat(),
        },
        headers=headers_conductor_de(id_conductor),
    )
    assert respuesta_solicitud.status_code == 200, respuesta_solicitud.text
    validar_contrato(respuesta_solicitud)

    id_vencida = _insertar_solicitud(
        engine_contrato,
        id_conductor,
        vence_en=datetime.now(UTC) - timedelta(minutes=1),
    )
    respuesta_vencida = cliente.post(
        f"/api/v1/solicitudes/{id_vencida}",
        json={
            "respuesta": "RECHAZADO",
            "hora_rta": datetime.now(UTC).isoformat(),
        },
        headers=headers_conductor_de(id_conductor),
    )
    assert respuesta_vencida.status_code == 410, respuesta_vencida.text
    validar_contrato(respuesta_vencida)
