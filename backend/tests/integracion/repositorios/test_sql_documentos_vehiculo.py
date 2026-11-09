"""`SqlRepositorioDocumentosVehiculo(session)`: el puerto sobre PostgreSQL.

Diseno que fijan los tests (igual que el fake `RepositorioDocumentosVehiculoEnMemoria`):
- `guardar` inserta el documento del vehiculo con `tipo` (`SEGURO`, `CEDULA_VERDE` o `VTV`),
  `numero` obligatorio, `entidad_emisora` opcional, las fechas y `url_archivo`; asigna id y
  hace `flush` (no `commit`).
- `listar_por_vehiculo` y `listar_por_vehiculos` devuelven los documentos en orden de alta
  (id ascendente); el lote trae una clave por cada id pedido (lista vacia si no tiene) y `{}`
  con una secuencia vacia.
- La base es la ultima defensa: rechaza un `tipo` invalido, un vencimiento no posterior a la
  emision y un numero en blanco (`CHECK`), y no deja borrar un vehiculo con documentos
  (`FK ... ON DELETE RESTRICT`).
Las lecturas de verificacion se hacen desde una sesion nueva.
"""

from datetime import date

import pytest
from app.dominio.documento_vehiculo import DocumentoVehiculo, TipoDocumentoVehiculo
from app.infraestructura.db.modelos import Conductor as ConductorOrm
from app.infraestructura.db.modelos import Vehiculo as VehiculoOrm
from app.infraestructura.repositorios.sql_documentos_vehiculo import (
    SqlRepositorioDocumentosVehiculo,
)
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

SEGURO = TipoDocumentoVehiculo.SEGURO
CEDULA_VERDE = TipoDocumentoVehiculo.CEDULA_VERDE
VTV = TipoDocumentoVehiculo.VTV
EMISION = date(2026, 1, 1)
VENCIMIENTO = date(2027, 1, 1)
URL = "https://almacen.example.com/vehiculos/documento.pdf"


@pytest.fixture
def repositorio(sesion_bd):
    return SqlRepositorioDocumentosVehiculo(sesion_bd)


def sembrar_conductor(sesion, dni="30123456"):
    fila = ConductorOrm(
        dni=dni,
        nombre="Ana",
        apellido="Perez",
        telefono="+54 379 4000000",
        email="ana@example.com",
    )
    sesion.add(fila)
    sesion.flush()
    return fila.id_conductor


def sembrar_vehiculo(sesion, id_conductor, patente="AAA111"):
    fila = VehiculoOrm(
        id_conductor=id_conductor,
        patente=patente,
        marca="Toyota",
        modelo="Etios",
        anio=2019,
        tipo="AUTO",
    )
    sesion.add(fila)
    sesion.flush()
    return fila.id_vehiculo


def documento(
    tipo=SEGURO,
    numero="POL-123",
    entidad_emisora="La Segunda",
    fecha_emision=EMISION,
    fecha_vencimiento=VENCIMIENTO,
    url_archivo=URL,
):
    return DocumentoVehiculo.crear(
        tipo=tipo,
        numero=numero,
        entidad_emisora=entidad_emisora,
        fecha_emision=fecha_emision,
        fecha_vencimiento=fecha_vencimiento,
        url_archivo=url_archivo,
    )


def listar_desde_otra_sesion(fabrica_sesiones, id_vehiculo):
    with fabrica_sesiones() as otra_sesion:
        return SqlRepositorioDocumentosVehiculo(otra_sesion).listar_por_vehiculo(id_vehiculo)


def ids(documentos):
    return [documento.id for documento in documentos]


def tipos(documentos):
    return [documento.tipo for documento in documentos]


# --- guardar y listar ---


@pytest.mark.parametrize("tipo", [SEGURO, CEDULA_VERDE, VTV])
def test_guardar_un_documento_le_asigna_id_y_persiste_todos_sus_campos(
    repositorio, sesion_bd, fabrica_sesiones, tipo
):
    id_conductor = sembrar_conductor(sesion_bd)
    id_vehiculo = sembrar_vehiculo(sesion_bd, id_conductor)

    guardado = repositorio.guardar(id_vehiculo, documento(tipo=tipo, numero=f"N-{tipo.value}"))
    sesion_bd.commit()

    [leido] = listar_desde_otra_sesion(fabrica_sesiones, id_vehiculo)
    assert isinstance(guardado, DocumentoVehiculo)
    assert guardado.id == 1
    assert leido.id == guardado.id
    assert leido.tipo is tipo
    assert leido.numero == f"N-{tipo.value}"
    assert leido.entidad_emisora == "La Segunda"
    assert leido.fecha_emision == EMISION
    assert leido.fecha_vencimiento == VENCIMIENTO
    assert leido.url_archivo == URL


def test_entidad_emisora_es_opcional(repositorio, sesion_bd, fabrica_sesiones):
    id_conductor = sembrar_conductor(sesion_bd)
    id_vehiculo = sembrar_vehiculo(sesion_bd, id_conductor)

    repositorio.guardar(id_vehiculo, documento(entidad_emisora=None))
    sesion_bd.commit()

    [leido] = listar_desde_otra_sesion(fabrica_sesiones, id_vehiculo)
    assert leido.entidad_emisora is None


def test_listar_por_vehiculo_devuelve_solo_los_suyos_en_orden_de_alta(
    repositorio, sesion_bd, fabrica_sesiones
):
    id_conductor = sembrar_conductor(sesion_bd)
    un_vehiculo = sembrar_vehiculo(sesion_bd, id_conductor, "AAA111")
    otro_vehiculo = sembrar_vehiculo(sesion_bd, id_conductor, "BBB222")
    primero = repositorio.guardar(un_vehiculo, documento(numero="POL-1"))
    repositorio.guardar(otro_vehiculo, documento(numero="POL-2"))
    tercero = repositorio.guardar(un_vehiculo, documento(tipo=VTV, numero="VTV-1"))
    sesion_bd.commit()

    resultado = listar_desde_otra_sesion(fabrica_sesiones, un_vehiculo)

    assert ids(resultado) == [primero.id, tercero.id]
    assert tipos(resultado) == [SEGURO, VTV]


def test_listar_por_vehiculo_sin_documentos_o_inexistente_devuelve_lista_vacia(repositorio):
    assert repositorio.listar_por_vehiculo(999) == []


def test_listar_por_vehiculos_devuelve_una_clave_por_id_pedido_y_ordena_por_id(
    repositorio, sesion_bd, fabrica_sesiones
):
    id_conductor = sembrar_conductor(sesion_bd)
    con_documentos = sembrar_vehiculo(sesion_bd, id_conductor, "AAA111")
    sin_documentos = sembrar_vehiculo(sesion_bd, id_conductor, "BBB222")
    primero = repositorio.guardar(con_documentos, documento(numero="POL-1"))
    segundo = repositorio.guardar(con_documentos, documento(tipo=VTV, numero="VTV-1"))
    sesion_bd.commit()

    with fabrica_sesiones() as otra_sesion:
        resultado = SqlRepositorioDocumentosVehiculo(otra_sesion).listar_por_vehiculos(
            [sin_documentos, con_documentos]
        )

    assert list(resultado) == [sin_documentos, con_documentos]
    assert resultado[sin_documentos] == []
    assert ids(resultado[con_documentos]) == [primero.id, segundo.id]


def test_listar_por_vehiculos_sin_ids_devuelve_un_diccionario_vacio(repositorio):
    assert repositorio.listar_por_vehiculos([]) == {}


def test_listar_por_vehiculos_con_ids_inexistentes_devuelve_listas_vacias(repositorio):
    assert repositorio.listar_por_vehiculos([998, 999]) == {998: [], 999: []}


# --- la base rechaza datos invalidos (CHECK) ---


@pytest.mark.parametrize(
    "actualizacion",
    [
        pytest.param("SET tipo = 'PATENTE'", id="tipo_invalido"),
        pytest.param("SET fecha_vencimiento = fecha_emision", id="vence_igual_a_emision"),
        pytest.param("SET fecha_vencimiento = DATE '2025-01-01'", id="vence_antes_de_emision"),
        pytest.param("SET numero = '   '", id="numero_en_blanco"),
    ],
)
def test_la_base_rechaza_documentos_invalidos(repositorio, sesion_bd, actualizacion):
    id_conductor = sembrar_conductor(sesion_bd)
    id_vehiculo = sembrar_vehiculo(sesion_bd, id_conductor)
    guardado = repositorio.guardar(id_vehiculo, documento())
    sesion_bd.commit()

    with pytest.raises(IntegrityError):
        sesion_bd.execute(
            text(f"UPDATE vehiculo_documento {actualizacion} WHERE id_documento = :id"),
            {"id": guardado.id},
        )
    sesion_bd.rollback()


# --- FK ON DELETE RESTRICT ---


def test_no_se_puede_guardar_un_documento_para_un_vehiculo_inexistente(repositorio):
    with pytest.raises(IntegrityError):
        repositorio.guardar(999, documento())


def test_no_se_puede_borrar_un_vehiculo_con_documentos(repositorio, sesion_bd):
    id_conductor = sembrar_conductor(sesion_bd)
    id_vehiculo = sembrar_vehiculo(sesion_bd, id_conductor)
    repositorio.guardar(id_vehiculo, documento())
    sesion_bd.commit()

    with pytest.raises(IntegrityError):
        sesion_bd.execute(text("DELETE FROM vehiculo WHERE id_vehiculo = :id"), {"id": id_vehiculo})
    sesion_bd.rollback()

    assert len(repositorio.listar_por_vehiculo(id_vehiculo)) == 1
