from datetime import date

import pytest
from app.api.esquemas.conductor import ConductorCreate, EstadoOperativo, conductor_desde_detalle
from app.api.esquemas.documento import DocumentoConductorCreate
from app.api.esquemas.estado import EstadoConductor as EstadoConductorRespuesta
from app.api.esquemas.estado import (
    EstadoConductorRequest,
    UbicacionConductor,
)
from app.api.esquemas.estado import EstadoOperativo as EstadoOperativoEstado
from app.api.esquemas.habilitacion import (
    HabilitacionAccionRequest,
    HabilitacionEvento,
)
from app.api.esquemas.solicitud import (
    EstadoSolicitud as EstadoSolicitudEsquema,
)
from app.api.esquemas.solicitud import RespuestaSolicitudRequest
from app.api.esquemas.solicitud import Solicitud as SolicitudRespuesta
from app.api.esquemas.vehiculo import VehiculoCreate
from app.aplicacion.casos_de_uso.resultados import ConductorDetalle
from app.dominio.conductor import Conductor, EstadoConductor
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


@pytest.mark.parametrize(
    ("estado_dominio", "estado_esperado"),
    [
        (EstadoConductor.DESCONECTADO, EstadoOperativo.DESCONECTADO),
        (EstadoConductor.CONECTADO, EstadoOperativo.CONECTADO),
        (EstadoConductor.DISPONIBLE, EstadoOperativo.DISPONIBLE),
        (EstadoConductor.OCUPADO, EstadoOperativo.OCUPADO),
    ],
)
def test_estado_operativo_del_conductor_se_deriva_de_su_estado_actual(
    estado_dominio: EstadoConductor,
    estado_esperado: EstadoOperativo,
) -> None:
    conductor = Conductor.crear(
        dni="12345678",
        nombre="Ana",
        apellido="Pérez",
        telefono="3415550000",
        email="ana@example.com",
    )
    conductor.id = 1
    conductor.estado = estado_dominio

    respuesta = conductor_desde_detalle(
        ConductorDetalle(conductor=conductor, documentos=[], vehiculos=[])
    )

    assert respuesta.estado == estado_esperado
    assert respuesta.conectado is (estado_dominio is not EstadoConductor.DESCONECTADO)
    assert respuesta.disponible is (estado_dominio is EstadoConductor.DISPONIBLE)


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


def test_estado_operativo_tiene_los_cuatro_estados() -> None:
    assert {estado.value for estado in EstadoOperativoEstado} == {
        "DESCONECTADO",
        "CONECTADO",
        "DISPONIBLE",
        "OCUPADO",
    }


def test_estado_conductor_no_incluye_la_ubicacion() -> None:
    respuesta = EstadoConductorRespuesta(
        id_conductor=1,
        estado="DISPONIBLE",
        actualizado="2026-11-02T01:30:00Z",
    )

    assert respuesta.id_vehiculo_activo is None
    assert set(EstadoConductorRespuesta.model_fields) == {
        "id_conductor",
        "estado",
        "id_vehiculo_activo",
        "actualizado",
    }


def test_ubicacion_conductor_admite_los_tres_campos_nulos() -> None:
    ubicacion = UbicacionConductor(id_conductor=1, latitud=None, longitud=None, fecha_act_ubic=None)

    assert ubicacion.latitud is None
    assert ubicacion.longitud is None
    assert ubicacion.fecha_act_ubic is None


def test_estado_request_exige_al_menos_un_campo() -> None:
    with pytest.raises(ValidationError):
        EstadoConductorRequest()


@pytest.mark.parametrize("estado", ["DESCONECTADO", "CONECTADO", "DISPONIBLE"])
def test_estado_request_admite_los_estados_pedibles(estado: str) -> None:
    assert EstadoConductorRequest(estado=estado).estado.value == estado


def test_estado_request_rechaza_ocupado() -> None:
    with pytest.raises(ValidationError):
        EstadoConductorRequest(estado="OCUPADO")


def test_estado_request_admite_solo_el_vehiculo_activo_incluso_nulo() -> None:
    pedido = EstadoConductorRequest(id_vehiculo_activo=None)

    assert "id_vehiculo_activo" in pedido.model_fields_set
    assert pedido.id_vehiculo_activo is None


@pytest.mark.parametrize(
    "datos",
    [{"latitud": -27.4}, {"longitud": -58.9}],
    ids=["solo-latitud", "solo-longitud"],
)
def test_estado_request_exige_latitud_y_longitud_juntas(datos: dict) -> None:
    with pytest.raises(ValidationError):
        EstadoConductorRequest(**datos)


@pytest.mark.parametrize(
    "datos",
    [
        {"latitud": 91, "longitud": 0},
        {"latitud": -91, "longitud": 0},
        {"latitud": 0, "longitud": 181},
        {"latitud": 0, "longitud": -181},
    ],
)
def test_estado_request_rechaza_coordenadas_fuera_de_rango(datos: dict) -> None:
    with pytest.raises(ValidationError):
        EstadoConductorRequest(**datos)


@pytest.mark.parametrize(
    "datos",
    [{"estado": None}, {"latitud": None, "longitud": None}],
    ids=["estado-nulo", "coordenadas-nulas"],
)
def test_estado_request_no_admite_nulos_en_estado_ni_en_coordenadas(datos: dict) -> None:
    with pytest.raises(ValidationError):
        EstadoConductorRequest(**datos)


def test_solicitud_tiene_los_campos_del_contrato() -> None:
    solicitud = SolicitudRespuesta(
        id=340,
        id_conductor=15,
        estado="PENDIENTE",
        vence_en="2026-10-03T18:45:30Z",
    )

    assert solicitud.id_viaje is None
    assert solicitud.respuesta is None
    assert solicitud.hora_rta is None
    assert set(SolicitudRespuesta.model_fields) == {
        "id",
        "id_conductor",
        "id_viaje",
        "estado",
        "vence_en",
        "respuesta",
        "hora_rta",
    }


def test_estado_solicitud_tiene_los_cuatro_estados() -> None:
    assert {estado.value for estado in EstadoSolicitudEsquema} == {
        "PENDIENTE",
        "ACEPTADO",
        "RECHAZADO",
        "VENCIDA",
    }


@pytest.mark.parametrize("respuesta", ["ACEPTADO", "RECHAZADO"])
def test_respuesta_solicitud_admite_aceptado_y_rechazado(respuesta: str) -> None:
    pedido = RespuestaSolicitudRequest(respuesta=respuesta, hora_rta="2026-10-03T18:44:10Z")

    assert pedido.respuesta.value == respuesta


@pytest.mark.parametrize(
    "datos",
    [
        {},
        {"respuesta": "ACEPTADO"},
        {"hora_rta": "2026-10-03T18:44:10Z"},
        {"respuesta": "PENDIENTE", "hora_rta": "2026-10-03T18:44:10Z"},
        {"respuesta": "VENCIDA", "hora_rta": "2026-10-03T18:44:10Z"},
        {"respuesta": "ACEPTADO", "hora_rta": "2026-10-03T18:44:10"},
        {"respuesta": "ACEPTADO", "hora_rta": "2026-10-03"},
    ],
    ids=[
        "vacio",
        "sin-hora",
        "sin-respuesta",
        "pendiente",
        "vencida",
        "hora-sin-zona",
        "solo-fecha",
    ],
)
def test_respuesta_solicitud_exige_respuesta_valida_y_hora(datos: dict) -> None:
    with pytest.raises(ValidationError):
        RespuestaSolicitudRequest(**datos)
