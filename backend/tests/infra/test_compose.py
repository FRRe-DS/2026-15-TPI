"""El Compose permite configurar la ubicación simulada de la API."""

from __future__ import annotations

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[3]
COMPOSE = RAIZ / "docker-compose.yml"
ENV_EXAMPLE = RAIZ / ".env.example"


def _compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


def test_el_servicio_api_expone_las_variables_de_ubicacion_simulada() -> None:
    entorno = _compose()["services"]["api"]["environment"]

    assert entorno["UBICACION_SIMULADA_LATITUD"] == "${UBICACION_SIMULADA_LATITUD:--27.4511}"
    assert entorno["UBICACION_SIMULADA_LONGITUD"] == "${UBICACION_SIMULADA_LONGITUD:--58.9867}"


def test_el_env_de_ejemplo_declara_las_variables_de_ubicacion_simulada() -> None:
    contenido = ENV_EXAMPLE.read_text(encoding="utf-8")

    assert "UBICACION_SIMULADA_LATITUD=-27.4511" in contenido
    assert "UBICACION_SIMULADA_LONGITUD=-58.9867" in contenido
