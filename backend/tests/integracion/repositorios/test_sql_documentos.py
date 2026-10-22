"""`SqlRepositorioDocumentos(session)`: el puerto `RepositorioDocumentos` sobre PostgreSQL.

- `guardar(id_conductor, documento)` inserta y devuelve el `Documento` de dominio con id
  asignado (1, 2, ...). Hace `flush`, no `commit`: los tests llaman a `sesion_bd.commit()` y
  leen desde otra sesion.
- `listar_por_conductor` devuelve solo los del conductor, en orden de alta (por id).
- Las fechas hacen ida y vuelta exactas como `date`. El estado VIGENTE/VENCIDO no se guarda
  (no hay columna): se calcula con `documento.estado_al(hoy)` del dominio.
- Guardar para un conductor inexistente propaga el `IntegrityError` de la FK sin traducir
  (CARACTERIZACION: el caso de uso ya valida antes); el INSERT va en un SAVEPOINT, asi que la
  sesion sigue usable.
"""

from datetime import date, datetime, timedelta

import pytest
from app.dominio.documento import Documento, EstadoDocumento, TipoDocumento
from app.infraestructura.db.modelos import Conductor as ConductorOrm
from app.infraestructura.repositorios.sql_documentos import SqlRepositorioDocumentos
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

HOY = date(2026, 6, 15)
URL = "https://almacen.example.com/licencias/lic.pdf"


@pytest.fixture
def repositorio(sesion_bd):
    return SqlRepositorioDocumentos(sesion_bd)


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


def nueva_licencia(numero="LIC-1", categoria="B1", vencimiento=date(2029, 1, 1)):
    return Documento.crear(
        tipo=TipoDocumento.LICENCIA,
        numero=numero,
        categoria=categoria,
        fecha_emision=date(2020, 1, 1),
        fecha_vencimiento=vencimiento,
        url_archivo=URL,
    )


def numeros(documentos):
    return [documento.numero for documento in documentos]


def test_guardar_devuelve_el_documento_de_dominio_con_ids_incrementales(repositorio, sesion_bd):
    id_conductor = sembrar_conductor(sesion_bd)

    primero = repositorio.guardar(id_conductor, nueva_licencia("LIC-1"))
    segundo = repositorio.guardar(id_conductor, nueva_licencia("LIC-2"))

    assert isinstance(primero, Documento)
    assert (primero.id, segundo.id) == (1, 2)
    assert primero.numero == "LIC-1"


def test_el_documento_confirmado_se_lee_con_todos_sus_campos_desde_otra_sesion(
    repositorio, sesion_bd, fabrica_sesiones
):
    id_conductor = sembrar_conductor(sesion_bd)
    guardado = repositorio.guardar(
        id_conductor,
        Documento.crear(
            tipo=TipoDocumento.LICENCIA,
            numero="LIC-123456",
            categoria="B1",
            fecha_emision=date(2024, 1, 10),
            fecha_vencimiento=date(2029, 1, 10),
            url_archivo=URL,
        ),
    )
    sesion_bd.commit()

    with fabrica_sesiones() as otra_sesion:
        [leido] = SqlRepositorioDocumentos(otra_sesion).listar_por_conductor(id_conductor)

    assert isinstance(leido, Documento)
    assert leido.id == guardado.id
    assert leido.tipo is TipoDocumento.LICENCIA
    assert leido.numero == "LIC-123456"
    assert leido.categoria == "B1"
    assert leido.fecha_emision == date(2024, 1, 10)
    assert leido.fecha_vencimiento == date(2029, 1, 10)
    assert leido.url_archivo == URL


def test_las_fechas_vuelven_como_date_sin_hora(repositorio, sesion_bd, fabrica_sesiones):
    id_conductor = sembrar_conductor(sesion_bd)
    repositorio.guardar(id_conductor, nueva_licencia(vencimiento=HOY))
    sesion_bd.commit()

    with fabrica_sesiones() as otra_sesion:
        [leido] = SqlRepositorioDocumentos(otra_sesion).listar_por_conductor(id_conductor)

    assert type(leido.fecha_emision) is date
    assert type(leido.fecha_vencimiento) is date
    assert not isinstance(leido.fecha_vencimiento, datetime)
    assert leido.fecha_vencimiento == HOY


def test_la_categoria_es_opcional_y_vuelve_como_none(repositorio, sesion_bd, fabrica_sesiones):
    id_conductor = sembrar_conductor(sesion_bd)
    repositorio.guardar(id_conductor, nueva_licencia(categoria=None))
    sesion_bd.commit()

    with fabrica_sesiones() as otra_sesion:
        [leido] = SqlRepositorioDocumentos(otra_sesion).listar_por_conductor(id_conductor)

    assert leido.categoria is None


@pytest.mark.parametrize(
    ("vencimiento", "estado_esperado"),
    [
        (HOY + timedelta(days=1), EstadoDocumento.VIGENTE),
        (HOY, EstadoDocumento.VIGENTE),
        (HOY - timedelta(days=1), EstadoDocumento.VENCIDO),
    ],
    ids=["vence_manana", "vence_hoy", "vencio_ayer"],
)
def test_el_documento_leido_calcula_su_estado_con_la_fecha_de_hoy(
    repositorio, sesion_bd, fabrica_sesiones, vencimiento, estado_esperado
):
    id_conductor = sembrar_conductor(sesion_bd)
    repositorio.guardar(id_conductor, nueva_licencia(vencimiento=vencimiento))
    sesion_bd.commit()

    with fabrica_sesiones() as otra_sesion:
        [leido] = SqlRepositorioDocumentos(otra_sesion).listar_por_conductor(id_conductor)

    assert leido.estado_al(HOY) is estado_esperado


def test_el_estado_del_documento_no_se_guarda_en_la_base(sesion_bd):
    columnas = {c["name"] for c in inspect(sesion_bd.get_bind()).get_columns("documento_conductor")}

    assert not any("estado" in columna for columna in columnas)


def test_listar_devuelve_solo_los_del_conductor_en_orden_de_alta(repositorio, sesion_bd):
    uno = sembrar_conductor(sesion_bd, "30000001")
    otro = sembrar_conductor(sesion_bd, "30000002")
    repositorio.guardar(uno, nueva_licencia("LIC-C"))
    repositorio.guardar(otro, nueva_licencia("LIC-AJENA"))
    repositorio.guardar(uno, nueva_licencia("LIC-A"))

    assert numeros(repositorio.listar_por_conductor(uno)) == ["LIC-C", "LIC-A"]
    assert numeros(repositorio.listar_por_conductor(otro)) == ["LIC-AJENA"]


def test_listar_de_un_conductor_sin_documentos_o_inexistente_devuelve_lista_vacia(
    repositorio, sesion_bd
):
    id_conductor = sembrar_conductor(sesion_bd)

    assert repositorio.listar_por_conductor(id_conductor) == []
    assert repositorio.listar_por_conductor(id_conductor + 1) == []


def test_guardar_para_un_conductor_inexistente_propaga_el_integrity_error_de_la_fk(
    repositorio, sesion_bd
):
    """Caracterizacion de lo que pasa hoy; el caso de uso valida el conductor antes."""
    id_conductor = sembrar_conductor(sesion_bd)

    with pytest.raises(IntegrityError):
        repositorio.guardar(id_conductor + 1, nueva_licencia("LIC-HUERFANA"))

    # La sesion sigue usable sin rollback manual y no quedo nada de la licencia huerfana.
    assert repositorio.listar_por_conductor(id_conductor) == []
    guardado = repositorio.guardar(id_conductor, nueva_licencia("LIC-VALIDA"))
    assert numeros(repositorio.listar_por_conductor(id_conductor)) == ["LIC-VALIDA"]
    assert guardado.id is not None
