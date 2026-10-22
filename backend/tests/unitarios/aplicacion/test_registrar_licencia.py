"""Caso de uso `registrar_licencia` (POST /conductores/{id}/documentacion).

Firmas bajo prueba:
    RegistrarLicencia(uow: UnidadDeTrabajo, reloj: Reloj)
    RegistrarLicencia.ejecutar(*, id_conductor, numero, categoria, fecha_emision,
                               fecha_vencimiento, url_archivo) -> DocumentoDeConductor
    DocumentoDeConductor(id_conductor: int, documento: Documento, estado: EstadoDocumento)
        corresponde al esquema DocumentoConductor del openapi (incluye id_conductor y
        estado); `documento` es la licencia guardada, con su id y `tipo` LICENCIA.

Reglas: el estado se calcula con `reloj.hoy()` (vence hoy es VIGENTE); la licencia queda
confirmada con `uow.commit()`; `NoEncontrado` si el conductor no existe; `DatosInvalidos`
si el vencimiento no es posterior a la emision, la URL es invalida o el numero esta vacio.
Ante un error no se persiste nada. Registrar una licencia no cambia la habilitacion.
"""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.aplicacion.casos_de_uso.registrar_licencia import RegistrarLicencia
from app.dominio.conductor import Conductor
from app.dominio.documento import EstadoDocumento, TipoDocumento
from app.dominio.errores import DatosInvalidos, NoEncontrado
from app.dominio.habilitacion import EstadoHabilitacion
from tests.unitarios.fakes.reloj_fijo import RelojFijo
from tests.unitarios.fakes.repositorios_en_memoria import UnidadDeTrabajoEnMemoria

AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
HOY = AHORA.date()
EMISION = date(2020, 1, 1)
URL = "https://almacen.example.com/licencias/lic.pdf"


@pytest.fixture
def uow():
    return UnidadDeTrabajoEnMemoria()


@pytest.fixture
def registrar_licencia(uow):
    return RegistrarLicencia(uow, RelojFijo(AHORA))


def sembrar_conductor(uow, dni="30123456"):
    conductor = Conductor.crear(
        dni=dni,
        nombre="Ana",
        apellido="Perez",
        telefono="+54 379 4000000",
        email="ana@example.com",
    )
    guardado = uow.conductores.guardar(conductor)
    uow.commit()
    return guardado


def datos_de_licencia(**cambios):
    datos = {
        "numero": "LIC-123456",
        "categoria": "B1",
        "fecha_emision": EMISION,
        "fecha_vencimiento": date(2029, 1, 1),
        "url_archivo": URL,
    }
    datos.update(cambios)
    return datos


@pytest.mark.parametrize(
    ("fecha_vencimiento", "estado_esperado"),
    [
        (HOY + timedelta(days=1), EstadoDocumento.VIGENTE),
        (HOY, EstadoDocumento.VIGENTE),
        (HOY - timedelta(days=1), EstadoDocumento.VENCIDO),
    ],
    ids=["vence_manana", "vence_hoy", "vencio_ayer"],
)
def test_devuelve_el_estado_calculado_con_la_fecha_del_reloj(
    registrar_licencia, uow, fecha_vencimiento, estado_esperado
):
    conductor = sembrar_conductor(uow)

    resultado = registrar_licencia.ejecutar(
        id_conductor=conductor.id,
        **datos_de_licencia(fecha_vencimiento=fecha_vencimiento),
    )

    assert resultado.estado is estado_esperado


def test_guarda_la_licencia_confirmada_y_la_devuelve_con_su_id(registrar_licencia, uow):
    conductor = sembrar_conductor(uow)

    resultado = registrar_licencia.ejecutar(
        id_conductor=conductor.id, **datos_de_licencia()
    )

    assert resultado.id_conductor == conductor.id
    assert resultado.documento.id is not None
    assert resultado.documento.tipo is TipoDocumento.LICENCIA
    [guardado] = uow.documentos.listar_por_conductor(conductor.id)
    assert guardado.id == resultado.documento.id
    assert guardado.tipo is TipoDocumento.LICENCIA
    assert guardado.numero == "LIC-123456"
    assert guardado.categoria == "B1"
    assert guardado.fecha_emision == EMISION
    assert guardado.fecha_vencimiento == date(2029, 1, 1)
    assert guardado.url_archivo == URL


def test_la_categoria_es_opcional(registrar_licencia, uow):
    conductor = sembrar_conductor(uow)

    resultado = registrar_licencia.ejecutar(
        id_conductor=conductor.id, **datos_de_licencia(categoria=None)
    )

    assert resultado.documento.categoria is None
    [guardado] = uow.documentos.listar_por_conductor(conductor.id)
    assert guardado.categoria is None


def test_la_licencia_de_un_conductor_no_aparece_en_otro(registrar_licencia, uow):
    conductor_a = sembrar_conductor(uow, "30000001")
    conductor_b = sembrar_conductor(uow, "30000002")

    registrar_licencia.ejecutar(id_conductor=conductor_a.id, **datos_de_licencia())

    assert len(uow.documentos.listar_por_conductor(conductor_a.id)) == 1
    assert uow.documentos.listar_por_conductor(conductor_b.id) == []


def test_registrar_una_licencia_no_cambia_la_habilitacion_del_conductor(
    registrar_licencia, uow
):
    conductor = sembrar_conductor(uow)

    registrar_licencia.ejecutar(id_conductor=conductor.id, **datos_de_licencia())

    assert uow.conductores.obtener(conductor.id).habilitacion is (
        EstadoHabilitacion.PENDIENTE
    )
    assert uow.habilitaciones.historial_conductor(conductor.id) == []


def test_lanza_no_encontrado_si_el_conductor_no_existe_y_no_guarda_nada(
    registrar_licencia, uow
):
    existente = sembrar_conductor(uow)
    id_inexistente = existente.id + 1

    with pytest.raises(NoEncontrado):
        registrar_licencia.ejecutar(id_conductor=id_inexistente, **datos_de_licencia())

    assert uow.documentos.listar_por_conductor(id_inexistente) == []
    assert uow.documentos.listar_por_conductor(existente.id) == []


@pytest.mark.parametrize(
    "dato_invalido",
    [
        {"fecha_vencimiento": EMISION},
        {"fecha_vencimiento": EMISION - timedelta(days=1)},
        {"url_archivo": "abc"},
        {"url_archivo": ""},
        {"numero": ""},
        {"numero": "   "},
    ],
    ids=[
        "vencimiento_igual_a_emision",
        "vencimiento_anterior_a_emision",
        "url_sin_esquema_ni_host",
        "url_vacia",
        "numero_vacio",
        "numero_solo_espacios",
    ],
)
def test_datos_invalidos_lanzan_error_y_no_persisten_nada(
    registrar_licencia, uow, dato_invalido
):
    conductor = sembrar_conductor(uow)

    with pytest.raises(DatosInvalidos):
        registrar_licencia.ejecutar(
            id_conductor=conductor.id, **datos_de_licencia(**dato_invalido)
        )

    assert uow.documentos.listar_por_conductor(conductor.id) == []
