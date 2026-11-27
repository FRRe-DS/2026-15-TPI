from pathlib import Path

from app.api.main import crear_app

CONTRATO = Path(__file__).resolve().parents[3] / "docs" / "contract" / "openapi.yaml"

# Los pares (ruta, método) del alcance implementado y su operationId.
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
    ("/api/v1/conductores/{id_conductor}/estado", "get"): "obtenerEstadoConductor",
    ("/api/v1/conductores/{id_conductor}/estado", "patch"): "actualizarEstadoConductor",
    ("/api/v1/conductores/{id_conductor}/ubicacion", "get"): "obtenerUbicacionConductor",
    ("/api/v1/conductores/{id_conductor}/solicitudes", "get"): "listarSolicitudesConductor",
    ("/api/v1/solicitudes/{id_solicitud}", "post"): "responderSolicitud",
    (
        "/api/v1/conductores/{id_conductor}/vehiculos/{id_vehiculo}/tipos-servicio",
        "get",
    ): "listarTiposServicioVehiculo",
    (
        "/api/v1/conductores/{id_conductor}/vehiculos/{id_vehiculo}/documentacion",
        "post",
    ): "crearDocumentacionVehiculo",
}


# Operaciones que el contrato 3.0.0 ya no tiene pero que el código todavía expone: se retiran en
# una PR siguiente, que cierra esta deuda antes de terminar la iteración. Aceptar o rechazar una
# oferta lo hace el conductor en M5.
RETIRADAS_DEL_CONTRATO = {"responderSolicitud"}


def _pares_generados() -> dict[tuple[str, str], str]:
    openapi = crear_app().openapi()
    pares: dict[tuple[str, str], str] = {}
    for ruta, operaciones in openapi["paths"].items():
        for metodo, operacion in operaciones.items():
            if metodo.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            pares[(ruta, metodo.lower())] = operacion["operationId"]
    return pares


def test_el_codigo_expone_17_operaciones() -> None:
    assert len(ESPERADOS) == 17
    assert len(set(ESPERADOS.values())) == 17


def test_genera_exactamente_los_pares_del_alcance() -> None:
    assert set(_pares_generados()) == set(ESPERADOS)


def test_los_operation_id_coinciden_con_el_contrato() -> None:
    assert _pares_generados() == ESPERADOS


def test_los_operation_id_existen_en_el_contrato_versionado() -> None:
    texto = CONTRATO.read_text(encoding="utf-8")

    for operation_id in set(ESPERADOS.values()) - RETIRADAS_DEL_CONTRATO:
        assert f"operationId: {operation_id}" in texto


def test_las_operaciones_retiradas_ya_no_estan_en_el_contrato() -> None:
    texto = CONTRATO.read_text(encoding="utf-8")

    for operation_id in RETIRADAS_DEL_CONTRATO:
        assert f"operationId: {operation_id}" not in texto
