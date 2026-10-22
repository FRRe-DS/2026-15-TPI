"""T094: ejemplos y consistencia del contrato en las 10 operaciones del alcance."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import pytest
import yaml

RAIZ_REPO = Path(__file__).resolve().parents[3]
RUTA_CONTRATO = RAIZ_REPO / "docs" / "contract" / "openapi.yaml"

# Las 10 operaciones del alcance de la Iteración 1 (spec.md, "Alcance").
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
]

IDS_OPERACIONES = [
    f"{metodo.upper()} {ruta}" for metodo, ruta in OPERACIONES_EN_ALCANCE
]

# Respuestas de error que T094 exige que tengan ejemplo.
ERRORES_OBLIGATORIOS = ("400", "401", "403", "404", "409", "422")

# Códigos del catálogo (specs/iteracion1/contracts/errores.md) válidos por estado.
CODIGOS_POR_ESTADO = {
    "400": {"SOLICITUD_INVALIDA"},
    "401": {"NO_AUTENTICADO"},
    "403": {"SIN_PERMISOS"},
    "404": {"NO_ENCONTRADO"},
    "409": {"DNI_DUPLICADO", "PATENTE_DUPLICADA", "TRANSICION_INVALIDA"},
    "422": {"DATOS_INVALIDOS", "LICENCIA_VIGENTE_REQUERIDA"},
}

PATRON_OPERATION_ID = re.compile(r"^[a-z][a-zA-Z0-9]*$")
PATRON_ESQUEMA = re.compile(r"^[A-Z][A-Za-z0-9]*$")
PATRON_PROPIEDAD = re.compile(r"^[a-z][a-z0-9_]*$")
PATRON_SEGMENTO = re.compile(r"^[a-z0-9_.~{}-]+$")


@pytest.fixture(scope="module")
def contrato() -> dict[str, Any]:
    with RUTA_CONTRATO.open(encoding="utf-8") as archivo:
        return yaml.safe_load(archivo)


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
        return [
            ejemplo["value"]
            for ejemplo in medio["examples"].values()
            if "value" in ejemplo
        ]
    esquema = _resolver(contrato, medio.get("schema", {}))
    if "example" in esquema:
        return [esquema["example"]]
    if "examples" in esquema:
        return list(esquema["examples"])
    return []


def _tiene_acentos(texto: str) -> bool:
    return any(
        unicodedata.combining(caracter)
        for caracter in unicodedata.normalize("NFKD", texto)
    )


def _esquemas_del_alcance(contrato: dict[str, Any]) -> set[str]:
    """Nombres de los esquemas alcanzables desde las 10 operaciones."""
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


@pytest.mark.parametrize(
    ("metodo", "ruta"), OPERACIONES_EN_ALCANCE, ids=IDS_OPERACIONES
)
def test_cada_cuerpo_de_peticion_tiene_ejemplo(
    contrato: dict[str, Any], metodo: str, ruta: str
) -> None:
    operacion = contrato["paths"][ruta][metodo]
    cuerpo = operacion.get("requestBody")
    if cuerpo is None:
        return  # La operación no recibe cuerpo.
    ejemplos = _ejemplos(contrato, cuerpo.get("content"))
    assert ejemplos, f"{metodo.upper()} {ruta} no tiene example en el requestBody"


@pytest.mark.parametrize(
    ("metodo", "ruta"), OPERACIONES_EN_ALCANCE, ids=IDS_OPERACIONES
)
def test_cada_respuesta_2xx_tiene_ejemplo(
    contrato: dict[str, Any], metodo: str, ruta: str
) -> None:
    respuestas = contrato["paths"][ruta][metodo]["responses"]
    exitosas = [codigo for codigo in respuestas if codigo.startswith("2")]
    assert exitosas, f"{metodo.upper()} {ruta} no declara una respuesta 2xx"
    for codigo in exitosas:
        respuesta = _resolver(contrato, respuestas[codigo])
        assert _ejemplos(contrato, respuesta.get("content")), (
            f"{metodo.upper()} {ruta} no tiene example en la respuesta {codigo}"
        )


@pytest.mark.parametrize(
    ("metodo", "ruta"), OPERACIONES_EN_ALCANCE, ids=IDS_OPERACIONES
)
def test_cada_respuesta_de_error_tiene_ejemplo_del_catalogo(
    contrato: dict[str, Any], metodo: str, ruta: str
) -> None:
    respuestas = contrato["paths"][ruta][metodo]["responses"]
    declarados = [codigo for codigo in ERRORES_OBLIGATORIOS if codigo in respuestas]
    for codigo in declarados:
        respuesta = _resolver(contrato, respuestas[codigo])
        ejemplos = _ejemplos(contrato, respuesta.get("content"))
        assert ejemplos, (
            f"{metodo.upper()} {ruta} no tiene example en la respuesta {codigo}"
        )
        for ejemplo in ejemplos:
            assert isinstance(ejemplo, dict), (
                f"El example de {codigo} en {metodo.upper()} {ruta} debe ser un objeto"
            )
            assert {"codigo", "mensaje"} <= ejemplo.keys(), (
                f"El example de {codigo} en {metodo.upper()} {ruta} "
                "debe tener codigo y mensaje"
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
            assert PATRON_SEGMENTO.fullmatch(segmento), (
                f"Segmento inválido en {ruta}: {segmento!r}"
            )
        assert segmentos[0].endswith("s"), (
            f"El recurso base de {ruta} debe ir en plural"
        )


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
        assert PATRON_ESQUEMA.fullmatch(nombre), (
            f"Nombre de esquema inválido: {nombre!r}"
        )
        assert not _tiene_acentos(nombre), f"Esquema con tildes: {nombre!r}"

        esquema = _resolver(contrato, {"$ref": f"#/components/schemas/{nombre}"})
        for propiedad in esquema.get("properties", {}):
            assert PATRON_PROPIEDAD.fullmatch(propiedad), (
                f"Propiedad inválida en {nombre}: {propiedad!r}"
            )
            assert not _tiene_acentos(propiedad), (
                f"Propiedad con tildes en {nombre}: {propiedad!r}"
            )
