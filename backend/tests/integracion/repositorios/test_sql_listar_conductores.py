"""`ListarConductores` sobre `SqlUnidadDeTrabajo` y PostgreSQL: sin consultas N+1.

El caso de uso real, con los repositorios SQL, emite un numero de SELECT que no depende de la
cantidad de conductores (uno para los conductores y consultas por lote para vehiculos, sus
tipos de servicio y documentos), y devuelve lo esperado: conductores en orden de alta,
documentos con el estado calculado por el reloj y los vehiculos propios de cada conductor.
"""

from datetime import UTC, date, datetime

import pytest
from app.aplicacion.casos_de_uso.listar_conductores import ListarConductores
from app.dominio.conductor import Conductor
from app.dominio.documento import Documento, EstadoDocumento, TipoDocumento
from app.dominio.vehiculo import TipoServicio, TipoVehiculo, Vehiculo
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


def sembrar_conductor_n(sesion, n):
    """El conductor n tiene n % 3 vehiculos (con 2 servicios cada uno) y n % 2 + 1 licencias.

    Las licencias de numero par vencen hoy (VIGENTE) y las de numero impar vencieron ayer.
    """
    conductores = SqlRepositorioConductores(sesion)
    vehiculos = SqlRepositorioVehiculos(sesion)
    documentos = SqlRepositorioDocumentos(sesion)
    conductor = conductores.guardar(
        Conductor.crear(
            dni=f"3000{n:04d}",
            nombre=f"Conductor{n}",
            apellido="Perez",
            telefono="+54 379 4000000",
            email="ana@example.com",
        )
    )
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
