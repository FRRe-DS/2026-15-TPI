"""T612: matriz de roles con tokens reales de Keycloak.

Requiere el stack de Docker Compose levantado y el seed cargado. Los tokens se
obtienen con password grant del realm ``m3``; no se firman tokens de prueba.
El usuario ``conductor.m3`` representa al conductor ``1`` del seed y
``servicio.m4`` es la cuenta tecnica de solo lectura.

La matriz verificada es la de
``specs/iteracion2-backend/contracts/token-jwt.md``.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

pytestmark = pytest.mark.e2e

BASE = "/api/v1/conductores"
SOLICITUDES = "/api/v1/solicitudes"
ID_CONDUCTOR_SEED = 1
ID_INEXISTENTE = 999_999

ALTA_CONDUCTOR = {
    "dni": "30111222",
    "nombre": "Cuenta",
    "apellido": "Servicio",
    "telefono": "+5493624000000",
    "email": "servicio.m4@m3.local",
}

LICENCIA = {
    "tipo": "LICENCIA",
    "numero": "LIC-SERVICIO",
    "categoria": "B1",
    "fecha_emision": "2026-01-01",
    "fecha_vencimiento": "2027-01-01",
    "url_archivo": "https://archivos.example/licencia-servicio.pdf",
}

VEHICULO = {
    "tipo": "AUTO",
    "patente": "AB123CD",
    "marca": "Toyota",
    "modelo": "Corolla",
    "anio": 2020,
    "tipos_serv": ["PASAJEROS"],
}

ACCION_HABILITACION = {
    "accion": "APROBAR",
    "motivo": "Intento de escritura con rol servicio",
}

DOCUMENTO_VEHICULO = {
    "tipo": "SEGURO",
    "numero": "POL-SERVICIO",
    "entidad_emisora": "La Segunda",
    "fecha_emision": "2026-01-01",
    "fecha_vencimiento": "2027-01-01",
    "url_archivo": "https://archivos.example/seguro-servicio.pdf",
}

ESTADO = {"estado": "CONECTADO"}

RESPUESTA_SOLICITUD = {
    "respuesta": "RECHAZADO",
    "hora_rta": "2026-11-09T12:00:00Z",
}

# Operaciones de escritura de la matriz: el servicio siempre recibe 403.
OPERACIONES_ESCRITURA = [
    pytest.param("post", BASE, ALTA_CONDUCTOR, id="1-alta-conductor"),
    pytest.param(
        "post",
        f"{BASE}/{ID_INEXISTENTE}/habilitacion",
        ACCION_HABILITACION,
        id="5-habilitacion-conductor",
    ),
    pytest.param(
        "post",
        f"{BASE}/{ID_INEXISTENTE}/documentacion",
        LICENCIA,
        id="6-documentacion-conductor",
    ),
    pytest.param(
        "post",
        f"{BASE}/{ID_INEXISTENTE}/vehiculos",
        VEHICULO,
        id="7-alta-vehiculo",
    ),
    pytest.param(
        "post",
        f"{BASE}/{ID_INEXISTENTE}/vehiculos/{ID_INEXISTENTE}/habilitacion",
        ACCION_HABILITACION,
        id="10-habilitacion-vehiculo",
    ),
    pytest.param(
        "post",
        f"{BASE}/{ID_INEXISTENTE}/vehiculos/{ID_INEXISTENTE}/documentacion",
        DOCUMENTO_VEHICULO,
        id="12-documentacion-vehiculo",
    ),
    pytest.param(
        "patch",
        f"{BASE}/{ID_INEXISTENTE}/estado",
        ESTADO,
        id="14-actualizar-estado",
    ),
    pytest.param(
        "post",
        f"{SOLICITUDES}/{ID_INEXISTENTE}",
        RESPUESTA_SOLICITUD,
        id="17-responder-solicitud",
    ),
]


def _pedir(
    cliente: httpx.Client,
    metodo: str,
    ruta: str,
    *,
    headers: dict[str, str],
    cuerpo: Any = None,
) -> httpx.Response:
    if cuerpo is None:
        return getattr(cliente, metodo)(ruta, headers=headers)
    return getattr(cliente, metodo)(ruta, json=cuerpo, headers=headers)


def test_servicio_lee_los_endpoints_permitidos(
    cliente_api: httpx.Client,
    headers_servicio: dict[str, str],
) -> None:
    listado = _pedir(cliente_api, "get", BASE, headers=headers_servicio)
    assert listado.status_code == 200, listado.text
    assert isinstance(listado.json(), list)
    assert listado.json()

    detalle = _pedir(
        cliente_api,
        "get",
        f"{BASE}/{ID_CONDUCTOR_SEED}",
        headers=headers_servicio,
    )
    assert detalle.status_code == 200, detalle.text
    assert detalle.json()["id"] == ID_CONDUCTOR_SEED

    habilitacion = _pedir(
        cliente_api,
        "get",
        f"{BASE}/{ID_CONDUCTOR_SEED}/habilitacion",
        headers=headers_servicio,
    )
    assert habilitacion.status_code == 200, habilitacion.text
    assert habilitacion.json()["id_conductor"] == ID_CONDUCTOR_SEED

    vehiculos = _pedir(
        cliente_api,
        "get",
        f"{BASE}/{ID_CONDUCTOR_SEED}/vehiculos",
        headers=headers_servicio,
    )
    assert vehiculos.status_code == 200, vehiculos.text
    assert vehiculos.json()
    id_vehiculo = vehiculos.json()[0]["id"]

    detalle_vehiculo = _pedir(
        cliente_api,
        "get",
        f"{BASE}/{ID_CONDUCTOR_SEED}/vehiculos/{id_vehiculo}",
        headers=headers_servicio,
    )
    assert detalle_vehiculo.status_code == 200, detalle_vehiculo.text
    assert detalle_vehiculo.json()["id"] == id_vehiculo

    tipos_servicio = _pedir(
        cliente_api,
        "get",
        f"{BASE}/{ID_CONDUCTOR_SEED}/vehiculos/{id_vehiculo}/tipos-servicio",
        headers=headers_servicio,
    )
    assert tipos_servicio.status_code == 200, tipos_servicio.text
    assert tipos_servicio.json()
    assert set(tipos_servicio.json()[0]) == {"tipo", "habilitado"}

    estado = _pedir(
        cliente_api,
        "get",
        f"{BASE}/{ID_CONDUCTOR_SEED}/estado",
        headers=headers_servicio,
    )
    assert estado.status_code == 200, estado.text
    assert estado.json()["id_conductor"] == ID_CONDUCTOR_SEED

    ubicacion = _pedir(
        cliente_api,
        "get",
        f"{BASE}/{ID_CONDUCTOR_SEED}/ubicacion",
        headers=headers_servicio,
    )
    assert ubicacion.status_code == 200, ubicacion.text
    assert ubicacion.json()["id_conductor"] == ID_CONDUCTOR_SEED


def test_servicio_no_lista_solicitudes(
    cliente_api: httpx.Client,
    headers_servicio: dict[str, str],
) -> None:
    respuesta = _pedir(
        cliente_api,
        "get",
        f"{BASE}/{ID_CONDUCTOR_SEED}/solicitudes",
        headers=headers_servicio,
    )

    assert respuesta.status_code == 403, respuesta.text
    assert respuesta.json()["codigo"] == "SIN_PERMISOS"


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo"), OPERACIONES_ESCRITURA)
def test_servicio_recibe_403_en_toda_escritura(
    cliente_api: httpx.Client,
    headers_servicio: dict[str, str],
    metodo: str,
    ruta: str,
    cuerpo: dict[str, Any],
) -> None:
    respuesta = _pedir(
        cliente_api,
        metodo,
        ruta,
        headers=headers_servicio,
        cuerpo=cuerpo,
    )

    assert respuesta.status_code == 403, respuesta.text
    assert respuesta.json()["codigo"] == "SIN_PERMISOS"


def test_conductor_no_puede_listar_conductores(
    cliente_api: httpx.Client,
    headers_conductor: dict[str, str],
) -> None:
    respuesta = _pedir(cliente_api, "get", BASE, headers=headers_conductor)

    assert respuesta.status_code == 403, respuesta.text
    assert respuesta.json()["codigo"] == "SIN_PERMISOS"


def test_conductor_solo_accede_a_su_propio_detalle(
    cliente_api: httpx.Client,
    headers_conductor: dict[str, str],
    headers_operador: dict[str, str],
) -> None:
    propio = _pedir(
        cliente_api,
        "get",
        f"{BASE}/{ID_CONDUCTOR_SEED}",
        headers=headers_conductor,
    )
    assert propio.status_code == 200, propio.text
    assert propio.json()["id"] == ID_CONDUCTOR_SEED

    listado = _pedir(cliente_api, "get", BASE, headers=headers_operador)
    assert listado.status_code == 200, listado.text
    otro = next(
        (conductor["id"] for conductor in listado.json() if conductor["id"] != ID_CONDUCTOR_SEED),
        None,
    )
    assert otro is not None, "El seed debe tener al menos otro conductor"

    ajeno = _pedir(
        cliente_api,
        "get",
        f"{BASE}/{otro}",
        headers=headers_conductor,
    )
    assert ajeno.status_code == 403, ajeno.text
    assert ajeno.json()["codigo"] == "ACCESO_PROHIBIDO"


def test_conductor_sobre_un_conductor_inexistente_recibe_403_y_no_404(
    cliente_api: httpx.Client,
    headers_conductor: dict[str, str],
) -> None:
    respuesta = _pedir(
        cliente_api,
        "get",
        f"{BASE}/{ID_INEXISTENTE}",
        headers=headers_conductor,
    )

    assert respuesta.status_code == 403, respuesta.text
    assert respuesta.json()["codigo"] == "ACCESO_PROHIBIDO"
