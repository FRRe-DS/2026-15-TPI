from pathlib import Path

import pytest
import yaml
from openapi_spec_validator import validate

OPERACIONES = [
    ("/conductores", "post"),
    ("/conductores", "get"),
    ("/conductores/{id_conductor}", "get"),
    ("/conductores/{id_conductor}/habilitacion", "get"),
    ("/conductores/{id_conductor}/habilitacion", "post"),
    ("/conductores/{id_conductor}/documentacion", "post"),
    ("/conductores/{id_conductor}/vehiculos", "post"),
    ("/conductores/{id_conductor}/vehiculos", "get"),
    ("/conductores/{id_conductor}/vehiculos/{id_vehiculo}", "get"),
    ("/conductores/{id_conductor}/vehiculos/{id_vehiculo}/habilitacion", "post"),
]

# Acciones de habilitación: exigen rol operador, por eso declaran 403
ACCIONES_OPERADOR = [
    ("/conductores/{id_conductor}/habilitacion", "post"),
    ("/conductores/{id_conductor}/vehiculos/{id_vehiculo}/habilitacion", "post"),
]

# Errores esperados según la operación (de contracts/errores.md y T094)
ERRORES_ESPERADOS = {
    ("/conductores", "post"): {"400", "409"},
    ("/conductores", "get"): {"400"},
    ("/conductores/{id_conductor}", "get"): {"404"},
    ("/conductores/{id_conductor}/habilitacion", "get"): {"404"},
    ("/conductores/{id_conductor}/habilitacion", "post"): {"400", "404", "409", "422"},
    ("/conductores/{id_conductor}/documentacion", "post"): {"400", "404", "422"},
    ("/conductores/{id_conductor}/vehiculos", "post"): {"400", "404", "409"},
    ("/conductores/{id_conductor}/vehiculos", "get"): {"404"},
    ("/conductores/{id_conductor}/vehiculos/{id_vehiculo}", "get"): {"404"},
    (
        "/conductores/{id_conductor}/vehiculos/{id_vehiculo}/habilitacion",
        "post",
    ): {"403", "404", "409"},
}


@pytest.fixture(scope="module")
def spec():
    ruta = Path(__file__).parents[3] / "docs" / "contract" / "openapi.yaml"
    assert ruta.exists(), f"No se encontro openapi.yaml en {ruta}"
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_openapi_es_una_especificacion_valida(spec):
    validate(spec)


@pytest.mark.parametrize(("ruta", "metodo"), OPERACIONES)
def test_define_la_operacion_del_alcance(spec, ruta, metodo):
    assert ruta in spec["paths"], f"Falta la ruta {ruta}"
    assert metodo in spec["paths"][ruta], f"Falta {metodo.upper()} {ruta}"


@pytest.mark.parametrize(("ruta", "metodo"), OPERACIONES)
def test_declara_401(spec, ruta, metodo):
    respuestas = spec["paths"][ruta][metodo]["responses"]
    assert "401" in respuestas, f"{metodo.upper()} {ruta} sin respuesta 401"


@pytest.mark.parametrize(("ruta", "metodo"), ACCIONES_OPERADOR)
def test_acciones_de_operador_declaran_403(spec, ruta, metodo):
    respuestas = spec["paths"][ruta][metodo]["responses"]
    assert "403" in respuestas, f"{metodo.upper()} {ruta} sin respuesta 403"


@pytest.mark.parametrize(("ruta", "metodo"), OPERACIONES)
def test_declara_las_respuestas_de_error(spec, ruta, metodo):
    respuestas = set(spec["paths"][ruta][metodo]["responses"])
    faltantes = ERRORES_ESPERADOS[(ruta, metodo)] - respuestas
    assert not faltantes, f"{metodo.upper()} {ruta} sin respuestas {sorted(faltantes)}"