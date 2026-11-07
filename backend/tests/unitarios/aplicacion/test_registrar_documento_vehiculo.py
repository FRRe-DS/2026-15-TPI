"""Caso de uso `registrar_documento_vehiculo`
(POST /conductores/{id}/vehiculos/{id_vehiculo}/documentacion).

Firmas bajo prueba:
    RegistrarDocumentoVehiculo(uow: UnidadDeTrabajo, reloj: Reloj)
    RegistrarDocumentoVehiculo.ejecutar(*, id_conductor, id_vehiculo,
                                        tipo: TipoDocumentoVehiculo, numero,
                                        entidad_emisora, fecha_emision,
                                        fecha_vencimiento, url_archivo)
        -> DocumentoDeVehiculo
    DocumentoDeVehiculo(id_vehiculo, documento: DocumentoVehiculo, estado: EstadoDocumento)

Guarda el documento del vehiculo y devuelve su estado `VIGENTE` o `VENCIDO` calculado con
`reloj.hoy()`. Un vencimiento no posterior a la emision lanza DatosInvalidos y no guarda
nada. Lanza NoEncontrado si el vehiculo no existe o es de otro conductor.
"""

from datetime import UTC, date, datetime

import pytest
from app.aplicacion.casos_de_uso.registrar_documento_vehiculo import (
    RegistrarDocumentoVehiculo,
)
from app.dominio.conductor import Conductor
from app.dominio.documento import EstadoDocumento
from app.dominio.documento_vehiculo import TipoDocumentoVehiculo
from app.dominio.errores import DatosInvalidos, NoEncontrado
from app.dominio.vehiculo import TipoServicio, TipoVehiculo, Vehiculo

from tests.unitarios.fakes.reloj_fijo import RelojFijo
from tests.unitarios.fakes.repositorios_en_memoria import UnidadDeTrabajoEnMemoria

HOY = date(2026, 6, 15)
AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
URL_ARCHIVO = "https://archivos.example.com/seguro.pdf"


@pytest.fixture
def uow():
    return UnidadDeTrabajoEnMemoria()


@pytest.fixture
def registrar_documento(uow):
    return RegistrarDocumentoVehiculo(uow, RelojFijo(AHORA))


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


def sembrar_vehiculo(uow, id_conductor, patente="AB123CD"):
    vehiculo = Vehiculo.crear(
        tipo=TipoVehiculo.AUTO,
        patente=patente,
        marca="Toyota",
        modelo="Etios",
        anio=2019,
        tipos_servicio=[TipoServicio.PASAJEROS],
    )
    vehiculo.id_conductor = id_conductor
    guardado = uow.vehiculos.guardar(vehiculo)
    uow.commit()
    return guardado


def datos_del_documento(**cambios):
    datos = {
        "tipo": TipoDocumentoVehiculo.SEGURO,
        "numero": "SEG-123",
        "entidad_emisora": "La Segunda",
        "fecha_emision": date(2026, 1, 1),
        "fecha_vencimiento": date(2027, 1, 1),
        "url_archivo": URL_ARCHIVO,
    }
    return {**datos, **cambios}


def test_guarda_el_documento_y_lo_devuelve_con_su_id_y_el_vehiculo(registrar_documento, uow):
    conductor = sembrar_conductor(uow)
    vehiculo = sembrar_vehiculo(uow, conductor.id)

    resultado = registrar_documento.ejecutar(
        id_conductor=conductor.id, id_vehiculo=vehiculo.id, **datos_del_documento()
    )

    guardados = uow.documentos_vehiculo.listar_por_vehiculo(vehiculo.id)
    assert guardados == [resultado.documento]
    assert resultado.id_vehiculo == vehiculo.id
    assert resultado.documento.id is not None
    assert resultado.documento.tipo is TipoDocumentoVehiculo.SEGURO
    assert resultado.documento.numero == "SEG-123"
    assert resultado.documento.entidad_emisora == "La Segunda"
    assert resultado.documento.url_archivo == URL_ARCHIVO


def test_el_documento_queda_confirmado_en_la_unidad_de_trabajo(registrar_documento, uow):
    conductor = sembrar_conductor(uow)
    vehiculo = sembrar_vehiculo(uow, conductor.id)

    registrar_documento.ejecutar(
        id_conductor=conductor.id, id_vehiculo=vehiculo.id, **datos_del_documento()
    )
    uow.rollback()

    assert len(uow.documentos_vehiculo.listar_por_vehiculo(vehiculo.id)) == 1


def test_un_documento_que_vence_en_el_futuro_queda_vigente(registrar_documento, uow):
    conductor = sembrar_conductor(uow)
    vehiculo = sembrar_vehiculo(uow, conductor.id)

    resultado = registrar_documento.ejecutar(
        id_conductor=conductor.id,
        id_vehiculo=vehiculo.id,
        **datos_del_documento(fecha_vencimiento=date(2026, 12, 31)),
    )

    assert resultado.estado is EstadoDocumento.VIGENTE


def test_un_documento_que_vence_hoy_queda_vigente(registrar_documento, uow):
    conductor = sembrar_conductor(uow)
    vehiculo = sembrar_vehiculo(uow, conductor.id)

    resultado = registrar_documento.ejecutar(
        id_conductor=conductor.id,
        id_vehiculo=vehiculo.id,
        **datos_del_documento(fecha_vencimiento=HOY),
    )

    assert resultado.estado is EstadoDocumento.VIGENTE


def test_un_documento_vencido_antes_de_hoy_queda_vencido(registrar_documento, uow):
    conductor = sembrar_conductor(uow)
    vehiculo = sembrar_vehiculo(uow, conductor.id)

    resultado = registrar_documento.ejecutar(
        id_conductor=conductor.id,
        id_vehiculo=vehiculo.id,
        **datos_del_documento(fecha_emision=date(2025, 1, 1), fecha_vencimiento=date(2026, 6, 14)),
    )

    assert resultado.estado is EstadoDocumento.VENCIDO


@pytest.mark.parametrize(
    "fecha_vencimiento",
    [date(2026, 1, 1), date(2025, 12, 31)],
    ids=["igual_a_la_emision", "anterior_a_la_emision"],
)
def test_vencimiento_no_posterior_a_la_emision_lanza_datos_invalidos_y_no_guarda(
    registrar_documento, uow, fecha_vencimiento
):
    conductor = sembrar_conductor(uow)
    vehiculo = sembrar_vehiculo(uow, conductor.id)

    with pytest.raises(DatosInvalidos):
        registrar_documento.ejecutar(
            id_conductor=conductor.id,
            id_vehiculo=vehiculo.id,
            **datos_del_documento(fecha_vencimiento=fecha_vencimiento),
        )

    assert uow.documentos_vehiculo.listar_por_vehiculo(vehiculo.id) == []


def test_lanza_no_encontrado_si_el_vehiculo_no_existe_y_no_guarda(registrar_documento, uow):
    conductor = sembrar_conductor(uow)
    vehiculo = sembrar_vehiculo(uow, conductor.id)

    with pytest.raises(NoEncontrado):
        registrar_documento.ejecutar(
            id_conductor=conductor.id, id_vehiculo=vehiculo.id + 1, **datos_del_documento()
        )

    assert uow.documentos_vehiculo.listar_por_vehiculo(vehiculo.id + 1) == []


def test_lanza_no_encontrado_si_el_vehiculo_es_de_otro_conductor_y_no_guarda(
    registrar_documento, uow
):
    duenio = sembrar_conductor(uow, "30000001")
    otro = sembrar_conductor(uow, "30000002")
    vehiculo_del_duenio = sembrar_vehiculo(uow, duenio.id)

    with pytest.raises(NoEncontrado):
        registrar_documento.ejecutar(
            id_conductor=otro.id, id_vehiculo=vehiculo_del_duenio.id, **datos_del_documento()
        )

    assert uow.documentos_vehiculo.listar_por_vehiculo(vehiculo_del_duenio.id) == []
