"""Caso de uso `obtener_conductor` (GET /conductores/{id}).

Firmas bajo prueba:
    ObtenerConductor(uow: UnidadDeTrabajo, reloj: Reloj)
    ObtenerConductor.ejecutar(*, id_conductor) -> ConductorDetalle

Devuelve el conductor con sus documentos (estado VIGENTE/VENCIDO calculado con
`reloj.hoy()`) y sus vehiculos, solo los suyos. Lanza NoEncontrado si el id no existe.
"""

from datetime import UTC, date, datetime

import pytest

from app.aplicacion.casos_de_uso.obtener_conductor import ObtenerConductor
from app.dominio.conductor import Conductor
from app.dominio.documento import Documento, EstadoDocumento, TipoDocumento
from app.dominio.errores import NoEncontrado
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.vehiculo import TipoServicio, TipoVehiculo, Vehiculo
from tests.unitarios.fakes.reloj_fijo import RelojFijo
from tests.unitarios.fakes.repositorios_en_memoria import UnidadDeTrabajoEnMemoria

HOY = date(2026, 6, 15)
AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)


@pytest.fixture
def uow():
    return UnidadDeTrabajoEnMemoria()


@pytest.fixture
def obtener_conductor(uow):
    return ObtenerConductor(uow, RelojFijo(AHORA))


def guardar_conductor(uow, dni, **estado):
    conductor = Conductor.crear(
        dni=dni,
        nombre="Ana",
        apellido="Perez",
        telefono="+54 379 4000000",
        email="ana@example.com",
    )
    for atributo, valor in estado.items():
        setattr(conductor, atributo, valor)
    guardado = uow.conductores.guardar(conductor)
    uow.commit()
    return guardado


def guardar_vehiculo(uow, id_conductor, patente):
    vehiculo = Vehiculo.crear(
        tipo=TipoVehiculo.AUTO,
        patente=patente,
        marca="Toyota",
        modelo="Etios",
        anio=2019,
        tipos_servicio=[TipoServicio.PASAJEROS],
    )
    vehiculo.id_conductor = id_conductor
    uow.vehiculos.guardar(vehiculo)
    uow.commit()


def guardar_licencia(uow, id_conductor, numero, fecha_vencimiento):
    licencia = Documento.crear(
        tipo=TipoDocumento.LICENCIA,
        numero=numero,
        categoria=None,
        fecha_emision=date(2020, 1, 1),
        fecha_vencimiento=fecha_vencimiento,
        url_archivo="https://almacen.example.com/licencias/lic.pdf",
    )
    uow.documentos.guardar(id_conductor, licencia)
    uow.commit()


def test_devuelve_los_datos_del_conductor(obtener_conductor, uow):
    guardado = guardar_conductor(
        uow,
        "30123456",
        habilitacion=EstadoHabilitacion.APROBADA,
        disponible=True,
    )

    conductor = obtener_conductor.ejecutar(id_conductor=guardado.id).conductor

    assert conductor.id == guardado.id
    assert conductor.dni == "30123456"
    assert conductor.nombre == "Ana"
    assert conductor.apellido == "Perez"
    assert conductor.telefono == "+54 379 4000000"
    assert conductor.email == "ana@example.com"
    assert conductor.habilitacion is EstadoHabilitacion.APROBADA
    assert conductor.conectado is False
    assert conductor.disponible is True


def test_devuelve_solo_el_conductor_pedido_con_sus_documentos_y_vehiculos(
    obtener_conductor, uow
):
    pedido = guardar_conductor(uow, "30000001")
    otro = guardar_conductor(uow, "30000002")
    guardar_licencia(uow, pedido.id, "LIC-PEDIDO", date(2029, 1, 1))
    guardar_licencia(uow, otro.id, "LIC-OTRO", date(2029, 1, 1))
    guardar_vehiculo(uow, pedido.id, "AAA111")
    guardar_vehiculo(uow, otro.id, "BBB222")

    detalle = obtener_conductor.ejecutar(id_conductor=pedido.id)

    assert detalle.conductor.dni == "30000001"
    assert [d.documento.numero for d in detalle.documentos] == ["LIC-PEDIDO"]
    assert [v.patente for v in detalle.vehiculos] == ["AAA111"]


def test_los_documentos_traen_el_estado_calculado_con_el_reloj(obtener_conductor, uow):
    conductor = guardar_conductor(uow, "30000001")
    guardar_licencia(uow, conductor.id, "VENCE-HOY", HOY)
    guardar_licencia(uow, conductor.id, "VENCIDA", date(2026, 6, 14))

    detalle = obtener_conductor.ejecutar(id_conductor=conductor.id)

    assert [(d.documento.numero, d.estado) for d in detalle.documentos] == [
        ("VENCE-HOY", EstadoDocumento.VIGENTE),
        ("VENCIDA", EstadoDocumento.VENCIDO),
    ]


def test_un_conductor_sin_documentos_ni_vehiculos_los_trae_vacios(
    obtener_conductor, uow
):
    conductor = guardar_conductor(uow, "30000001")

    detalle = obtener_conductor.ejecutar(id_conductor=conductor.id)

    assert detalle.documentos == []
    assert detalle.vehiculos == []


def test_lanza_no_encontrado_si_el_conductor_no_existe(obtener_conductor, uow):
    existente = guardar_conductor(uow, "30000001")

    with pytest.raises(NoEncontrado):
        obtener_conductor.ejecutar(id_conductor=existente.id + 1)
