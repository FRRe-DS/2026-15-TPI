"""Caso de uso `obtener_vehiculo` (GET /conductores/{id}/vehiculos/{id_vehiculo}).

Firmas bajo prueba:
    ObtenerVehiculo(uow: UnidadDeTrabajo, reloj: Reloj)
    ObtenerVehiculo.ejecutar(*, id_conductor, id_vehiculo) -> VehiculoDetalle
    VehiculoDetalle(vehiculo: Vehiculo, documentos: list[DocumentoVehiculoConEstado])
    DocumentoVehiculoConEstado(documento: DocumentoVehiculo, estado: EstadoDocumento)

Devuelve el vehiculo con todos sus datos y sus documentos en orden de alta, cada uno con su
estado `VIGENTE` o `VENCIDO` calculado con `reloj.hoy()` (lista vacia si no tiene). Lanza
NoEncontrado si el conductor no existe, si el vehiculo no existe o si el vehiculo es de otro
conductor.
"""

from datetime import UTC, date, datetime

import pytest
from app.aplicacion.casos_de_uso.obtener_vehiculo import ObtenerVehiculo
from app.dominio.conductor import Conductor
from app.dominio.documento import EstadoDocumento
from app.dominio.documento_vehiculo import DocumentoVehiculo, TipoDocumentoVehiculo
from app.dominio.errores import NoEncontrado
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.vehiculo import TipoServicio, TipoVehiculo, Vehiculo

from tests.unitarios.fakes.reloj_fijo import RelojFijo
from tests.unitarios.fakes.repositorios_en_memoria import UnidadDeTrabajoEnMemoria

AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)


@pytest.fixture
def uow():
    return UnidadDeTrabajoEnMemoria()


@pytest.fixture
def obtener_vehiculo(uow):
    return ObtenerVehiculo(uow, RelojFijo(AHORA))


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
        tipo=TipoVehiculo.MOTO,
        patente=patente,
        marca="Honda",
        modelo="Wave",
        anio=2021,
        tipos_servicio=[TipoServicio.PASAJEROS, TipoServicio.ENVIOS],
    )
    vehiculo.id_conductor = id_conductor
    vehiculo.habilitacion = EstadoHabilitacion.APROBADA
    vehiculo.tipos_servicio[1].habilitado = True  # ENVIOS habilitado, PASAJEROS no
    guardado = uow.vehiculos.guardar(vehiculo)
    uow.commit()
    return guardado


def sembrar_documento(uow, id_vehiculo, numero, fecha_vencimiento):
    documento = DocumentoVehiculo.crear(
        tipo=TipoDocumentoVehiculo.SEGURO,
        numero=numero,
        entidad_emisora=None,
        fecha_emision=date(2024, 1, 1),
        fecha_vencimiento=fecha_vencimiento,
        url_archivo="https://archivos.example.com/seguro.pdf",
    )
    guardado = uow.documentos_vehiculo.guardar(id_vehiculo, documento)
    uow.commit()
    return guardado


def test_devuelve_el_vehiculo_con_todos_sus_datos(obtener_vehiculo, uow):
    conductor = sembrar_conductor(uow)
    sembrado = sembrar_vehiculo(uow, conductor.id)

    detalle = obtener_vehiculo.ejecutar(id_conductor=conductor.id, id_vehiculo=sembrado.id)

    vehiculo = detalle.vehiculo
    assert vehiculo.id == sembrado.id
    assert vehiculo.id_conductor == conductor.id
    assert vehiculo.tipo is TipoVehiculo.MOTO
    assert vehiculo.patente == "AB123CD"
    assert vehiculo.marca == "Honda"
    assert vehiculo.modelo == "Wave"
    assert vehiculo.anio == 2021
    assert vehiculo.habilitacion is EstadoHabilitacion.APROBADA
    assert {s.tipo: s.habilitado for s in vehiculo.tipos_servicio} == {
        TipoServicio.PASAJEROS: False,
        TipoServicio.ENVIOS: True,
    }


def test_los_documentos_del_vehiculo_vienen_vacios(obtener_vehiculo, uow):
    conductor = sembrar_conductor(uow)
    sembrado = sembrar_vehiculo(uow, conductor.id)

    detalle = obtener_vehiculo.ejecutar(id_conductor=conductor.id, id_vehiculo=sembrado.id)

    assert detalle.documentos == []


def test_los_documentos_traen_su_estado_calculado_con_la_fecha_de_hoy(obtener_vehiculo, uow):
    conductor = sembrar_conductor(uow)
    sembrado = sembrar_vehiculo(uow, conductor.id)
    vigente = sembrar_documento(uow, sembrado.id, "VIGENTE-1", date(2027, 1, 1))
    vence_hoy = sembrar_documento(uow, sembrado.id, "HOY-1", date(2026, 6, 15))
    vencido = sembrar_documento(uow, sembrado.id, "VENCIDO-1", date(2026, 6, 14))

    detalle = obtener_vehiculo.ejecutar(id_conductor=conductor.id, id_vehiculo=sembrado.id)

    assert [(item.documento, item.estado) for item in detalle.documentos] == [
        (vigente, EstadoDocumento.VIGENTE),
        (vence_hoy, EstadoDocumento.VIGENTE),
        (vencido, EstadoDocumento.VENCIDO),
    ]


def test_no_mezcla_los_documentos_de_otro_vehiculo(obtener_vehiculo, uow):
    conductor = sembrar_conductor(uow)
    pedido = sembrar_vehiculo(uow, conductor.id, "AAA111")
    otro = sembrar_vehiculo(uow, conductor.id, "BBB222")
    propio = sembrar_documento(uow, pedido.id, "PROPIO-1", date(2027, 1, 1))
    sembrar_documento(uow, otro.id, "AJENO-1", date(2027, 1, 1))

    detalle = obtener_vehiculo.ejecutar(id_conductor=conductor.id, id_vehiculo=pedido.id)

    assert [item.documento for item in detalle.documentos] == [propio]


def test_lanza_no_encontrado_si_el_conductor_no_existe(obtener_vehiculo, uow):
    conductor = sembrar_conductor(uow)
    sembrado = sembrar_vehiculo(uow, conductor.id)

    with pytest.raises(NoEncontrado):
        obtener_vehiculo.ejecutar(id_conductor=conductor.id + 1, id_vehiculo=sembrado.id)


def test_lanza_no_encontrado_si_el_vehiculo_no_existe(obtener_vehiculo, uow):
    conductor = sembrar_conductor(uow)
    sembrado = sembrar_vehiculo(uow, conductor.id)

    with pytest.raises(NoEncontrado):
        obtener_vehiculo.ejecutar(id_conductor=conductor.id, id_vehiculo=sembrado.id + 1)


def test_lanza_no_encontrado_si_el_vehiculo_pertenece_a_otro_conductor(obtener_vehiculo, uow):
    duenio = sembrar_conductor(uow, "30000001")
    otro = sembrar_conductor(uow, "30000002")
    vehiculo_del_duenio = sembrar_vehiculo(uow, duenio.id)

    with pytest.raises(NoEncontrado):
        obtener_vehiculo.ejecutar(id_conductor=otro.id, id_vehiculo=vehiculo_del_duenio.id)
