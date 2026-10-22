from pathlib import Path

from app.api.main import crear_app

CONTRATO = Path(__file__).resolve().parents[3] / "docs" / "contract" / "openapi.yaml"

# Los 10 pares (ruta, método) del alcance de la Iteración 1 y su operationId.
ESPERADOS: dict[tuple[str, str], str] = {
    ("/api/v1/conductores", "post"): "crearConductor",
    ("/api/v1/conductores", "get"): "listarConductores",
    ("/api/v1/conductores/{id_conductor}", "get"): "obtenerConductor",
    (
        "/api/v1/conductores/{id_conductor}/habilitacion",
        "get",
    ): "obtenerHabilitacionConductor",
    (
        "/api/v1/conductores/{id_conductor}/habilitacion",
        "post",
    ): "accionHabilitacionConductor",
    (
        "/api/v1/conductores/{id_conductor}/documentacion",
        "post",
    ): "crearDocumentacionConductor",
    (
        "/api/v1/conductores/{id_conductor}/vehiculos",
        "post",
    ): "crearVehiculo",
    (
        "/api/v1/conductores/{id_conductor}/vehiculos",
        "get",
    ): "listarVehiculos",
    (
        "/api/v1/conductores/{id_conductor}/vehiculos/{id_vehiculo}",
        "get",
    ): "obtenerVehiculo",
    (
        "/api/v1/conductores/{id_conductor}/vehiculos/{id_vehiculo}/habilitacion",
        "post",
    ): "accionHabilitacionVehiculo",
}


def _pares_generados() -> dict[tuple[str, str], str]:
    openapi = crear_app().openapi()
    pares: dict[tuple[str, str], str] = {}
    for ruta, operaciones in openapi["paths"].items():
        for metodo, operacion in operaciones.items():
            if metodo.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            pares[(ruta, metodo.lower())] = operacion["operationId"]
    return pares


def test_genera_exactamente_los_10_pares_del_alcance() -> None:
    assert set(_pares_generados()) == set(ESPERADOS)


def test_los_operation_id_coinciden_con_el_contrato() -> None:
    assert _pares_generados() == ESPERADOS


def test_los_operation_id_existen_en_el_contrato_versionado() -> None:
    texto = CONTRATO.read_text(encoding="utf-8")

    for operation_id in ESPERADOS.values():
        assert f"operationId: {operation_id}" in texto
