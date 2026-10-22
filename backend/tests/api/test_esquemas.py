from datetime import date

import pytest
from app.api.esquemas.conductor import ConductorCreate
from app.api.esquemas.documento import DocumentoConductorCreate
from app.api.esquemas.habilitacion import (
    HabilitacionAccionRequest,
    HabilitacionEvento,
)
from app.api.esquemas.vehiculo import VehiculoCreate
from pydantic import ValidationError


@pytest.mark.parametrize("dni", ["1234567", "12345678"])
def test_dni_valido(dni: str) -> None:
    conductor = ConductorCreate(
        dni=dni,
        nombre="Ana",
        apellido="Pérez",
        telefono="3415550000",
        email="ana@example.com",
    )

    assert conductor.dni == dni


@pytest.mark.parametrize("dni", ["123456", "123456789", "1234567a", ""])
def test_dni_invalido(dni: str) -> None:
    with pytest.raises(ValidationError):
        ConductorCreate(
            dni=dni,
            nombre="Ana",
            apellido="Pérez",
            telefono="3415550000",
            email="ana@example.com",
        )


@pytest.mark.parametrize("email", ["sin-arroba", "a@b", "a b@c.com"])
def test_email_invalido(email: str) -> None:
    with pytest.raises(ValidationError):
        ConductorCreate(
            dni="12345678",
            nombre="Ana",
            apellido="Pérez",
            telefono="3415550000",
            email=email,
        )


def test_nombre_obligatorio() -> None:
    with pytest.raises(ValidationError):
        ConductorCreate(
            dni="12345678",
            nombre="",
            apellido="Pérez",
            telefono="3415550000",
            email="ana@example.com",
        )


@pytest.mark.parametrize("motivo", ["", None])
def test_motivo_de_habilitacion_obligatorio(motivo: str | None) -> None:
    with pytest.raises(ValidationError):
        HabilitacionAccionRequest(accion="APROBAR", motivo=motivo)


def test_accion_de_alta_no_se_acepta_en_la_solicitud() -> None:
    with pytest.raises(ValidationError):
        HabilitacionAccionRequest(accion="ALTA", motivo="Prueba")


def test_evento_acepta_alta_sin_estado_anterior() -> None:
    from datetime import UTC, datetime

    from app.api.esquemas.habilitacion import AccionHabilitacion, EstadoHabilitacion

    evento = HabilitacionEvento(
        accion=AccionHabilitacion.ALTA,
        estado_nuevo=EstadoHabilitacion.PENDIENTE,
        motivo="Alta del conductor",
        fecha=datetime.now(UTC),
    )

    assert evento.estado_anterior is None
    assert evento.id_operador is None


def _vehiculo(**cambios: object) -> dict[str, object]:
    datos: dict[str, object] = {
        "tipo": "AUTO",
        "patente": "AB123CD",
        "marca": "Toyota",
        "modelo": "Corolla",
        "anio": 2020,
        "tipos_serv": ["PASAJEROS"],
    }
    datos.update(cambios)
    return datos


def test_vehiculo_valido() -> None:
    vehiculo = VehiculoCreate(**_vehiculo())

    assert vehiculo.tipos_serv[0].value == "PASAJEROS"


@pytest.mark.parametrize(
    "tipos_serv",
    [[], ["PASAJEROS", "PASAJEROS"]],
    ids=["vacio", "repetido"],
)
def test_vehiculo_exige_tipos_de_servicio_unicos(
    tipos_serv: list[str],
) -> None:
    with pytest.raises(ValidationError):
        VehiculoCreate(**_vehiculo(tipos_serv=tipos_serv))


@pytest.mark.parametrize("anio", [1899, 2101])
def test_anio_fuera_de_rango(anio: int) -> None:
    with pytest.raises(ValidationError):
        VehiculoCreate(**_vehiculo(anio=anio))


def test_documento_valido() -> None:
    documento = DocumentoConductorCreate(
        numero="LIC-1",
        fecha_emision=date(2020, 1, 1),
        fecha_vencimiento=date(2030, 1, 1),
        url_archivo="https://archivos.example/licencia.pdf",
    )

    assert documento.tipo == "LICENCIA"


@pytest.mark.parametrize(
    "cambios",
    [
        {"url_archivo": "no-es-una-url"},
        {"fecha_emision": "2020-13-01"},
        {"numero": ""},
    ],
    ids=["url-invalida", "fecha-invalida", "numero-vacio"],
)
def test_documento_invalido(cambios: dict[str, str]) -> None:
    datos: dict[str, object] = {
        "numero": "LIC-1",
        "fecha_emision": date(2020, 1, 1),
        "fecha_vencimiento": date(2030, 1, 1),
        "url_archivo": "https://archivos.example/licencia.pdf",
    }
    datos.update(cambios)

    with pytest.raises(ValidationError):
        DocumentoConductorCreate(**datos)


def test_esquema_de_conductor_expone_restricciones_del_contrato() -> None:
    propiedades = ConductorCreate.model_json_schema()["properties"]

    assert propiedades["dni"]["pattern"] == "^[0-9]{7,8}$"
    assert propiedades["nombre"]["maxLength"] == 100
    assert propiedades["email"]["format"] == "email"


def test_esquema_de_habilitacion_expone_motivo_no_vacio() -> None:
    propiedades = HabilitacionAccionRequest.model_json_schema()["properties"]

    assert propiedades["motivo"]["minLength"] == 1
    assert propiedades["motivo"]["maxLength"] == 500


def test_esquema_de_vehiculo_expone_tipos_serv_unicos() -> None:
    propiedades = VehiculoCreate.model_json_schema()["properties"]

    assert propiedades["tipos_serv"]["minItems"] == 1
    assert propiedades["tipos_serv"]["uniqueItems"] is True
    assert propiedades["anio"]["minimum"] == 1900
    assert propiedades["anio"]["maximum"] == 2100


def test_esquema_de_documento_expone_formatos() -> None:
    propiedades = DocumentoConductorCreate.model_json_schema()["properties"]

    assert propiedades["fecha_emision"]["format"] == "date"
    assert propiedades["fecha_vencimiento"]["format"] == "date"
    assert propiedades["url_archivo"]["format"] == "uri"
