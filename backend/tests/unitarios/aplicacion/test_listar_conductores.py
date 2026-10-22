"""Caso de uso `listar_conductores` (GET /conductores).

Firmas bajo prueba:
    ListarConductores(uow: UnidadDeTrabajo, reloj: Reloj)
    ListarConductores.ejecutar(*, habilitado=None, disponible=None, tipo_vehiculo=None)
        -> list[ConductorDetalle]

Reglas: sin filtros devuelve todos (en orden de alta); `habilitado=True` solo APROBADA y
`habilitado=False` cualquier otro estado; `tipo_vehiculo` exige al menos un vehiculo de
ese tipo; los filtros se combinan con AND. Cada ConductorDetalle trae los documentos del
conductor como DocumentoConEstado (estado calculado con `reloj.hoy()`) y sus vehiculos.
"""

from datetime import UTC, date, datetime

import pytest

from app.aplicacion.casos_de_uso.listar_conductores import ListarConductores
from app.dominio.conductor import Conductor
from app.dominio.documento import Documento, EstadoDocumento, TipoDocumento
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
def listar_conductores(uow):
    return ListarConductores(uow, RelojFijo(AHORA))


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


def guardar_vehiculo(uow, id_conductor, patente, tipo=TipoVehiculo.AUTO):
    vehiculo = Vehiculo.crear(
        tipo=tipo,
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


def guardar_licencia(uow, id_conductor, numero, fecha_vencimiento):
    licencia = Documento.crear(
        tipo=TipoDocumento.LICENCIA,
        numero=numero,
        categoria=None,
        fecha_emision=date(2020, 1, 1),
        fecha_vencimiento=fecha_vencimiento,
        url_archivo="https://almacen.example.com/licencias/lic.pdf",
    )
    guardado = uow.documentos.guardar(id_conductor, licencia)
    uow.commit()
    return guardado


def dnis(detalles):
    return [detalle.conductor.dni for detalle in detalles]


def test_sin_conductores_devuelve_lista_vacia_sin_error(listar_conductores):
    assert listar_conductores.ejecutar() == []


def test_sin_filtros_devuelve_todos_los_conductores_en_orden_de_alta(
    listar_conductores, uow
):
    for dni in ("30000001", "30000002", "30000003"):
        guardar_conductor(uow, dni)

    assert dnis(listar_conductores.ejecutar()) == ["30000001", "30000002", "30000003"]


def test_habilitado_verdadero_devuelve_solo_los_aprobados(listar_conductores, uow):
    guardar_conductor(uow, "30000001", habilitacion=EstadoHabilitacion.APROBADA)
    guardar_conductor(uow, "30000002", habilitacion=EstadoHabilitacion.PENDIENTE)
    guardar_conductor(uow, "30000003", habilitacion=EstadoHabilitacion.SUSPENDIDA)

    assert dnis(listar_conductores.ejecutar(habilitado=True)) == ["30000001"]


def test_habilitado_falso_devuelve_los_que_no_estan_aprobados(listar_conductores, uow):
    guardar_conductor(uow, "30000001", habilitacion=EstadoHabilitacion.APROBADA)
    guardar_conductor(uow, "30000002", habilitacion=EstadoHabilitacion.PENDIENTE)
    guardar_conductor(uow, "30000003", habilitacion=EstadoHabilitacion.OBSERVADA)
    guardar_conductor(uow, "30000004", habilitacion=EstadoHabilitacion.SUSPENDIDA)
    guardar_conductor(uow, "30000005", habilitacion=EstadoHabilitacion.RECHAZADA)

    assert dnis(listar_conductores.ejecutar(habilitado=False)) == [
        "30000002",
        "30000003",
        "30000004",
        "30000005",
    ]


@pytest.mark.parametrize(
    ("disponible", "dnis_esperados"),
    [(True, ["30000001"]), (False, ["30000002"])],
)
def test_filtra_por_disponible(listar_conductores, uow, disponible, dnis_esperados):
    guardar_conductor(uow, "30000001", disponible=True)
    guardar_conductor(uow, "30000002", disponible=False)

    assert dnis(listar_conductores.ejecutar(disponible=disponible)) == dnis_esperados


def test_filtra_por_tipo_de_vehiculo_con_al_menos_uno_de_ese_tipo(
    listar_conductores, uow
):
    con_auto = guardar_conductor(uow, "30000001")
    con_moto = guardar_conductor(uow, "30000002")
    con_ambos = guardar_conductor(uow, "30000003")
    guardar_conductor(uow, "30000004")  # sin vehiculos
    guardar_vehiculo(uow, con_auto.id, "AAA111", TipoVehiculo.AUTO)
    guardar_vehiculo(uow, con_moto.id, "BBB222", TipoVehiculo.MOTO)
    guardar_vehiculo(uow, con_ambos.id, "CCC333", TipoVehiculo.AUTO)
    guardar_vehiculo(uow, con_ambos.id, "DDD444", TipoVehiculo.MOTO)

    con_tipo_auto = listar_conductores.ejecutar(tipo_vehiculo=TipoVehiculo.AUTO)
    con_tipo_moto = listar_conductores.ejecutar(tipo_vehiculo=TipoVehiculo.MOTO)

    assert dnis(con_tipo_auto) == ["30000001", "30000003"]
    assert dnis(con_tipo_moto) == ["30000002", "30000003"]


def test_combina_los_filtros_con_and(listar_conductores, uow):
    cumple_todo = guardar_conductor(
        uow, "30000001", habilitacion=EstadoHabilitacion.APROBADA, disponible=True
    )
    no_disponible = guardar_conductor(
        uow, "30000002", habilitacion=EstadoHabilitacion.APROBADA, disponible=False
    )
    no_aprobado = guardar_conductor(uow, "30000003", disponible=True)
    sin_el_tipo = guardar_conductor(
        uow, "30000004", habilitacion=EstadoHabilitacion.APROBADA, disponible=True
    )
    for conductor, patente in [
        (cumple_todo, "AAA111"),
        (no_disponible, "BBB222"),
        (no_aprobado, "CCC333"),
    ]:
        guardar_vehiculo(uow, conductor.id, patente, TipoVehiculo.AUTO)
    guardar_vehiculo(uow, sin_el_tipo.id, "DDD444", TipoVehiculo.MOTO)

    resultado = listar_conductores.ejecutar(
        habilitado=True, disponible=True, tipo_vehiculo=TipoVehiculo.AUTO
    )

    assert dnis(resultado) == ["30000001"]


def test_filtros_sin_coincidencias_devuelven_lista_vacia_sin_error(
    listar_conductores, uow
):
    guardar_conductor(uow, "30000001")

    assert listar_conductores.ejecutar(habilitado=True) == []


def test_cada_conductor_trae_sus_documentos_con_el_estado_calculado_con_el_reloj(
    listar_conductores, uow
):
    conductor = guardar_conductor(uow, "30000001")
    guardar_licencia(uow, conductor.id, "VENCE-HOY", HOY)
    guardar_licencia(uow, conductor.id, "VENCIDA", date(2026, 6, 14))
    guardar_licencia(uow, conductor.id, "FUTURA", date(2029, 1, 1))

    [detalle] = listar_conductores.ejecutar()

    assert [(d.documento.numero, d.estado) for d in detalle.documentos] == [
        ("VENCE-HOY", EstadoDocumento.VIGENTE),
        ("VENCIDA", EstadoDocumento.VENCIDO),
        ("FUTURA", EstadoDocumento.VIGENTE),
    ]


def test_cada_conductor_trae_solo_sus_propios_documentos_y_vehiculos(
    listar_conductores, uow
):
    uno = guardar_conductor(uow, "30000001")
    otro = guardar_conductor(uow, "30000002")
    guardar_licencia(uow, uno.id, "LIC-UNO", date(2029, 1, 1))
    guardar_licencia(uow, otro.id, "LIC-OTRO", date(2029, 1, 1))
    guardar_vehiculo(uow, uno.id, "AAA111")
    guardar_vehiculo(uow, otro.id, "BBB222")
    guardar_vehiculo(uow, otro.id, "CCC333")

    detalle_uno, detalle_otro = listar_conductores.ejecutar()

    assert [d.documento.numero for d in detalle_uno.documentos] == ["LIC-UNO"]
    assert [v.patente for v in detalle_uno.vehiculos] == ["AAA111"]
    assert [d.documento.numero for d in detalle_otro.documentos] == ["LIC-OTRO"]
    assert [v.patente for v in detalle_otro.vehiculos] == ["BBB222", "CCC333"]


def test_un_conductor_sin_documentos_ni_vehiculos_los_trae_vacios(
    listar_conductores, uow
):
    guardar_conductor(uow, "30000001")

    [detalle] = listar_conductores.ejecutar()

    assert detalle.documentos == []
    assert detalle.vehiculos == []


def test_el_estado_de_los_documentos_sigue_al_reloj(uow):
    reloj = RelojFijo(AHORA)
    conductor = guardar_conductor(uow, "30000001")
    guardar_licencia(uow, conductor.id, "VENCE-HOY", HOY)
    listar = ListarConductores(uow, reloj)

    [antes] = listar.ejecutar()
    reloj.avanzar(dias=1)
    [despues] = listar.ejecutar()

    assert antes.documentos[0].estado is EstadoDocumento.VIGENTE
    assert despues.documentos[0].estado is EstadoDocumento.VENCIDO
