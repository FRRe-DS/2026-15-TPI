import pytest
from app.api.errores import (
    ErrorAPI,
    limite_de_solicitudes,
    registrar_manejadores,
    servicio_temporalmente_no_disponible,
)
from app.dominio.errores import (
    AccesoProhibido,
    ConductorNoHabilitado,
    DatosInvalidos,
    DniDuplicado,
    LicenciaVigenteRequerida,
    NoEncontrado,
    PatenteDuplicada,
    RolNoAutorizado,
    SolicitudVencida,
    SolicitudYaRespondida,
    TransicionInvalida,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel


class Cuerpo(BaseModel):
    nombre: str


def _app_con_errores() -> FastAPI:
    app = FastAPI()
    registrar_manejadores(app)

    @app.get("/no-encontrado")
    def no_encontrado() -> None:
        raise NoEncontrado("No existe el conductor 1")

    @app.get("/dni-duplicado")
    def dni_duplicado() -> None:
        raise DniDuplicado("El DNI ya existe")

    @app.get("/patente-duplicada")
    def patente_duplicada() -> None:
        raise PatenteDuplicada("La patente ya existe")

    @app.get("/transicion-invalida")
    def transicion_invalida() -> None:
        raise TransicionInvalida("La acción no está permitida")

    @app.get("/licencia-requerida")
    def licencia_requerida() -> None:
        raise LicenciaVigenteRequerida("Se requiere una licencia vigente")

    @app.get("/datos-invalidos")
    def datos_invalidos() -> None:
        raise DatosInvalidos("El vencimiento debe ser posterior a la emisión")

    @app.get("/acceso-prohibido")
    def acceso_prohibido() -> None:
        raise AccesoProhibido("Solo podés operar sobre tus propios datos")

    @app.get("/rol-no-autorizado")
    def rol_no_autorizado() -> None:
        raise RolNoAutorizado("El rol del token no permite esta operación")

    @app.get("/solicitud-ya-respondida")
    def solicitud_ya_respondida() -> None:
        raise SolicitudYaRespondida("La solicitud ya fue respondida")

    @app.get("/solicitud-vencida")
    def solicitud_vencida() -> None:
        raise SolicitudVencida("La solicitud venció")

    @app.get("/conductor-no-habilitado")
    def conductor_no_habilitado() -> None:
        raise ConductorNoHabilitado("El conductor no está habilitado")

    @app.get("/error-api")
    def error_api() -> None:
        raise ErrorAPI(409, "CONFLICTO", "Conflicto de prueba")

    @app.get("/limite")
    def limite() -> None:
        raise limite_de_solicitudes(7)

    @app.get("/redis-no-disponible")
    def redis_no_disponible() -> None:
        raise servicio_temporalmente_no_disponible()

    @app.post("/validacion")
    def validacion(cuerpo: Cuerpo) -> dict[str, str]:
        return {"nombre": cuerpo.nombre}

    @app.get("/inesperado")
    def inesperado() -> None:
        raise RuntimeError("detalle interno que no debe exponerse")

    return app


@pytest.fixture
def client_errores() -> TestClient:
    app = _app_con_errores()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.mark.parametrize(
    ("ruta", "status_code", "codigo"),
    [
        ("/no-encontrado", 404, "NO_ENCONTRADO"),
        ("/dni-duplicado", 409, "DNI_DUPLICADO"),
        ("/patente-duplicada", 409, "PATENTE_DUPLICADA"),
        ("/transicion-invalida", 409, "TRANSICION_INVALIDA"),
        ("/licencia-requerida", 422, "LICENCIA_VIGENTE_REQUERIDA"),
        ("/datos-invalidos", 422, "DATOS_INVALIDOS"),
        ("/acceso-prohibido", 403, "ACCESO_PROHIBIDO"),
        ("/rol-no-autorizado", 403, "SIN_PERMISOS"),
        ("/solicitud-ya-respondida", 409, "SOLICITUD_YA_RESPONDIDA"),
        ("/solicitud-vencida", 410, "SOLICITUD_VENCIDA"),
        ("/conductor-no-habilitado", 422, "CONDUCTOR_NO_HABILITADO"),
        ("/error-api", 409, "CONFLICTO"),
    ],
)
def test_errores_de_dominio_mapean_al_catalogo(
    client_errores: TestClient,
    ruta: str,
    status_code: int,
    codigo: str,
) -> None:
    respuesta = client_errores.get(ruta)

    assert respuesta.status_code == status_code
    assert respuesta.json()["codigo"] == codigo
    assert respuesta.json()["mensaje"]


def test_validacion_de_forma_responde_400(
    client_errores: TestClient,
) -> None:
    respuesta = client_errores.post("/validacion", json={})

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "SOLICITUD_INVALIDA"


def test_excepcion_inesperada_responde_500_sin_detalles(
    client_errores: TestClient,
) -> None:
    respuesta = client_errores.get("/inesperado")

    assert respuesta.status_code == 500
    assert respuesta.json() == {
        "codigo": "ERROR_INTERNO",
        "mensaje": "Ocurrió un error interno",
    }
    assert "detalle interno" not in respuesta.text


def test_limite_responde_429_retry_after_y_no_cachea(
    client_errores: TestClient,
) -> None:
    respuesta = client_errores.get("/limite")

    assert respuesta.status_code == 429
    assert respuesta.json() == {
        "codigo": "LIMITE_DE_SOLICITUDES",
        "mensaje": "Se alcanzó el límite de solicitudes; reintente más tarde.",
    }
    assert respuesta.headers["Retry-After"] == "7"
    assert respuesta.headers["Cache-Control"] == "no-store"


def test_falla_redis_responde_503_sin_detalles_internos(
    client_errores: TestClient,
) -> None:
    respuesta = client_errores.get("/redis-no-disponible")

    assert respuesta.status_code == 503
    assert respuesta.json() == {
        "codigo": "SERVICIO_TEMPORALMENTE_NO_DISPONIBLE",
        "mensaje": "El servicio no está disponible temporalmente.",
    }


def test_ruta_inexistente_usa_el_formato_de_error(
    client_errores: TestClient,
) -> None:
    respuesta = client_errores.get("/no-existe")

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"


def test_catalogo_completo_se_registra() -> None:
    # Guarda de regresión: cada error de dominio del contrato tiene su mapeo.
    from app.api import errores

    mapeados = {excepcion for excepcion, _, _ in errores.MAPEO_ERRORES_DOMINIO}
    assert mapeados == {
        NoEncontrado,
        DniDuplicado,
        PatenteDuplicada,
        TransicionInvalida,
        LicenciaVigenteRequerida,
        DatosInvalidos,
        AccesoProhibido,
        RolNoAutorizado,
        SolicitudYaRespondida,
        SolicitudVencida,
        ConductorNoHabilitado,
    }
