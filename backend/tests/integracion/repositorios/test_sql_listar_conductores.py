"""`ListarConductores` sobre `SqlUnidadDeTrabajo` y PostgreSQL: sin consultas N+1.

El caso de uso real, con los repositorios SQL, emite un numero de SELECT que no depende de la
cantidad de conductores (uno para los conductores y consultas por lote para vehiculos, sus
tipos de servicio y documentos), y devuelve lo esperado: conductores en orden de alta,
documentos con el estado calculado por el reloj y los vehiculos propios de cada conductor.
"""

from datetime import UTC, date, datetime

import pytest
from app.aplicacion.casos_de_uso.listar_conductores import ListarConductores
from app.dominio.conductor import Conductor, EstadoConductor
from app.dominio.documento import Documento, EstadoDocumento, TipoDocumento
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.vehiculo import (
    ServicioDelVehiculo,
    TipoServicio,
    TipoVehiculo,
    Vehiculo,
)
from app.infraestructura.repositorios.sql_conductores import SqlRepositorioConductores
from app.infraestructura.repositorios.sql_documentos import SqlRepositorioDocumentos
from app.infraestructura.repositorios.sql_unidad_de_trabajo import SqlUnidadDeTrabajo
from app.infraestructura.repositorios.sql_vehiculos import SqlRepositorioVehiculos

from tests.integracion.sentencias import capturar_sentencias, selects
from tests.unitarios.fakes.reloj_fijo import RelojFijo

AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
HOY = AHORA.date()
MAXIMO_DE_SELECTS = 4  # conductores + vehiculos + servicios de los vehiculos + documentos


@pytest.fixture
def listar_conductores(fabrica_sesiones, sesion_bd):
    """Depende de `sesion_bd` para que la base se limpie al terminar cada prueba."""
    return ListarConductores(SqlUnidadDeTrabajo(fabrica_sesiones), RelojFijo(AHORA))


def sembrar_conductor_n(
    sesion,
    n,
    *,
    estado=EstadoConductor.DESCONECTADO,
    habilitacion=EstadoHabilitacion.PENDIENTE,
):
    """El conductor n tiene n % 3 vehiculos (con 2 servicios cada uno) y n % 2 + 1 licencias.

    Las licencias de numero par vencen hoy (VIGENTE) y las de numero impar vencieron ayer.
    """
    conductores = SqlRepositorioConductores(sesion)
    vehiculos = SqlRepositorioVehiculos(sesion)
    documentos = SqlRepositorioDocumentos(sesion)
    conductor = Conductor.crear(
        dni=f"3000{n:04d}",
        nombre=f"Conductor{n}",
        apellido="Perez",
        telefono="+54 379 4000000",
        email="ana@example.com",
    )
    conductor.estado = estado
    conductor.habilitacion = habilitacion
    conductor = conductores.guardar(conductor)
    patentes = []
    for k in range(n % 3):
        patente = f"C{n}V{k}"
        patentes.append(patente)
        vehiculo = Vehiculo.crear(
            tipo=TipoVehiculo.AUTO,
            patente=patente,
            marca="Toyota",
            modelo="Etios",
            anio=2019,
            tipos_servicio=[TipoServicio.PASAJEROS, TipoServicio.ENVIOS],
        )
        vehiculo.id_conductor = conductor.id
        vehiculos.guardar(vehiculo)
    esperados = []
    for k in range(n % 2 + 1):
        numero = f"C{n}L{k}"
        vence_hoy = k % 2 == 0
        documentos.guardar(
            conductor.id,
            Documento.crear(
                tipo=TipoDocumento.LICENCIA,
                numero=numero,
                categoria=None,
                fecha_emision=date(2020, 1, 1),
                fecha_vencimiento=HOY if vence_hoy else date(2026, 6, 14),
                url_archivo="https://almacen.example.com/lic.pdf",
            ),
        )
        esperados.append(
            (numero, EstadoDocumento.VIGENTE if vence_hoy else EstadoDocumento.VENCIDO)
        )
    return conductor.dni, patentes, esperados


def sembrar(sesion, desde, hasta):
    esperado = []
    for n in range(desde, hasta + 1):
        esperado.append(sembrar_conductor_n(sesion, n))
    sesion.commit()
    return esperado


def sembrar_conductor_con_vehiculo(sesion, dni, *, estado, habilitacion, tipo, servicios):
    conductores = SqlRepositorioConductores(sesion)
    vehiculos = SqlRepositorioVehiculos(sesion)
    conductor = Conductor.crear(
        dni=dni,
        nombre="Conductor",
        apellido="Perez",
        telefono="+54 379 4000000",
        email="ana@example.com",
    )
    conductor.estado = estado
    conductor.habilitacion = habilitacion
    conductor = conductores.guardar(conductor)
    vehiculo = Vehiculo.crear(
        tipo=tipo,
        patente=f"P{dni[-4:]}",
        marca="Toyota",
        modelo="Etios",
        anio=2019,
        tipos_servicio=list(servicios),
    )
    vehiculo.id_conductor = conductor.id
    vehiculo.habilitacion = habilitacion
    vehiculo.tipos_servicio = [ServicioDelVehiculo(servicio, True) for servicio in servicios]
    vehiculos.guardar(vehiculo)
    return conductor


@pytest.mark.parametrize(
    ("estado", "dni_esperado"),
    [
        (EstadoConductor.DESCONECTADO, "30000001"),
        (EstadoConductor.CONECTADO, "30000002"),
        (EstadoConductor.DISPONIBLE, "30000003"),
        (EstadoConductor.OCUPADO, "30000004"),
    ],
)
def test_el_filtro_estado_devuelve_solo_los_conductores_en_ese_estado(
    listar_conductores, sesion_bd, estado, dni_esperado
):
    for n, estado_sembrado in enumerate(EstadoConductor, start=1):
        sembrar_conductor_n(sesion_bd, n, estado=estado_sembrado)
    sesion_bd.commit()

    resultado = listar_conductores.ejecutar(estado=estado)

    assert [d.conductor.dni for d in resultado] == [dni_esperado]
    assert [d.conductor.estado for d in resultado] == [estado]


def test_estado_se_combina_con_tipo_servicio_y_los_demas_filtros(listar_conductores, sesion_bd):
    sembrar_conductor_con_vehiculo(
        sesion_bd,
        "30000001",
        estado=EstadoConductor.DISPONIBLE,
        habilitacion=EstadoHabilitacion.APROBADA,
        tipo=TipoVehiculo.AUTO,
        servicios=[TipoServicio.PASAJEROS],
    )
    sembrar_conductor_con_vehiculo(
        sesion_bd,
        "30000002",
        estado=EstadoConductor.CONECTADO,
        habilitacion=EstadoHabilitacion.APROBADA,
        tipo=TipoVehiculo.AUTO,
        servicios=[TipoServicio.PASAJEROS],
    )
    sembrar_conductor_con_vehiculo(
        sesion_bd,
        "30000003",
        estado=EstadoConductor.DISPONIBLE,
        habilitacion=EstadoHabilitacion.APROBADA,
        tipo=TipoVehiculo.MOTO,
        servicios=[TipoServicio.PASAJEROS],
    )
    sembrar_conductor_con_vehiculo(
        sesion_bd,
        "30000004",
        estado=EstadoConductor.DISPONIBLE,
        habilitacion=EstadoHabilitacion.APROBADA,
        tipo=TipoVehiculo.AUTO,
        servicios=[TipoServicio.ENVIOS],
    )
    sembrar_conductor_con_vehiculo(
        sesion_bd,
        "30000005",
        estado=EstadoConductor.DISPONIBLE,
        habilitacion=EstadoHabilitacion.PENDIENTE,
        tipo=TipoVehiculo.AUTO,
        servicios=[TipoServicio.PASAJEROS],
    )
    sesion_bd.commit()

    resultado = listar_conductores.ejecutar(
        habilitado=True,
        estado=EstadoConductor.DISPONIBLE,
        tipo_vehiculo=TipoVehiculo.AUTO,
        tipo_servicio=TipoServicio.PASAJEROS,
    )

    assert [d.conductor.dni for d in resultado] == ["30000001"]


def test_el_filtro_estado_no_agrega_consultas_por_fila(
    listar_conductores, sesion_bd, engine_integracion
):
    def selects_de_ejecutar():
        with capturar_sentencias(engine_integracion) as sentencias:
            resultado = listar_conductores.ejecutar(estado=EstadoConductor.DISPONIBLE)
        return len(selects(sentencias)), resultado

    for n in range(1, 3):
        sembrar_conductor_n(sesion_bd, n, estado=EstadoConductor.DISPONIBLE)
    sesion_bd.commit()
    selects_con_2, _ = selects_de_ejecutar()

    for n in range(3, 7):
        sembrar_conductor_n(sesion_bd, n, estado=EstadoConductor.DISPONIBLE)
    sesion_bd.commit()
    selects_con_6, resultado = selects_de_ejecutar()

    assert selects_con_2 == selects_con_6
    assert selects_con_6 <= MAXIMO_DE_SELECTS
    assert len(resultado) == 6
    assert all(d.conductor.estado is EstadoConductor.DISPONIBLE for d in resultado)


def test_el_total_de_selects_de_listar_conductores_no_crece_con_la_cantidad_de_conductores(
    listar_conductores, sesion_bd, engine_integracion
):
    def selects_de_ejecutar():
        with capturar_sentencias(engine_integracion) as sentencias:
            resultado = listar_conductores.ejecutar()
        return len(selects(sentencias)), resultado

    esperado = sembrar(sesion_bd, 1, 2)
    selects_con_2, _ = selects_de_ejecutar()
    esperado += sembrar(sesion_bd, 3, 6)
    selects_con_6, resultado = selects_de_ejecutar()

    assert selects_con_2 == selects_con_6
    assert selects_con_6 <= MAXIMO_DE_SELECTS
    assert [d.conductor.dni for d in resultado] == [dni for dni, _, _ in esperado]
    assert [[v.patente for v in d.vehiculos] for d in resultado] == [p for _, p, _ in esperado]
    assert [[(x.documento.numero, x.estado) for x in d.documentos] for d in resultado] == [
        docs for _, _, docs in esperado
    ]
    assert all(len(v.tipos_servicio) == 2 for d in resultado for v in d.vehiculos)
