"""`SqlRepositorioHabilitaciones(session)`: el puerto `RepositorioHabilitaciones` sobre PostgreSQL.

- El historial devuelve `EventoHabilitacion` de dominio con todos sus campos; `fecha` hace
  ida y vuelta como instante aware en UTC. El evento ALTA (estado_anterior e id_operador
  nulos) tambien. Orden: el de registro (por id), no el cronologico.
- Los historiales de conductor y de vehiculo son independientes aunque compartan numero de
  id (en estos tests ambos arrancan en 1). Sin eventos o con entidad inexistente: lista vacia.
- Los eventos son de solo escritura: la API publica del repositorio no ofrece actualizar ni
  borrar, y registrar un evento no cambia el estado de la entidad (eso lo hace el caso de uso).
- Un motivo vacio o solo espacios viola el CHECK de la base y una entidad inexistente viola
  la FK: ambos propagan el `IntegrityError` sin traducir y la sesion sigue usable (SAVEPOINT).
- `hace flush, no commit`: los tests llaman a `sesion_bd.commit()` y leen desde otra sesion.

Los tests parametrizados por entidad usan el mismo repositorio con los metodos de conductor
o de vehiculo segun corresponda.
"""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from app.dominio.habilitacion import (
    AccionHabilitacion,
    EstadoHabilitacion,
    EventoHabilitacion,
)
from app.infraestructura.db.modelos import Conductor as ConductorOrm
from app.infraestructura.db.modelos import Vehiculo as VehiculoOrm
from app.infraestructura.repositorios.sql_habilitaciones import SqlRepositorioHabilitaciones
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

PENDIENTE = EstadoHabilitacion.PENDIENTE
APROBADA = EstadoHabilitacion.APROBADA
FECHA = datetime(2026, 6, 15, 12, 30, 45, 123456, tzinfo=UTC)

CONDUCTOR = ("registrar_evento_conductor", "historial_conductor")
VEHICULO = ("registrar_evento_vehiculo", "historial_vehiculo")
POR_ENTIDAD = pytest.mark.parametrize(
    ("registrar", "historial"),
    [pytest.param(*CONDUCTOR, id="conductor"), pytest.param(*VEHICULO, id="vehiculo")],
)

METODOS_PUBLICOS_DEL_PUERTO = {
    "registrar_evento_conductor",
    "registrar_evento_vehiculo",
    "historial_conductor",
    "historial_vehiculo",
}


@pytest.fixture
def repositorio(sesion_bd):
    return SqlRepositorioHabilitaciones(sesion_bd)


@pytest.fixture
def entidades(sesion_bd):
    """Dos conductores (ids 1 y 2) y dos vehiculos (ids 1 y 2) del primer conductor."""
    for dni in ("30000001", "30000002"):
        sesion_bd.add(
            ConductorOrm(
                dni=dni,
                nombre="Ana",
                apellido="Perez",
                telefono="+54 379 4000000",
                email="ana@example.com",
            )
        )
    sesion_bd.flush()
    for patente in ("AAA111", "BBB222"):
        sesion_bd.add(
            VehiculoOrm(
                id_conductor=1,
                patente=patente,
                marca="Toyota",
                modelo="Etios",
                anio=2019,
                tipo="AUTO",
            )
        )
    sesion_bd.flush()


def evento(motivo="Documentacion revisada", fecha=FECHA, **cambios):
    datos = {
        "accion": AccionHabilitacion.APROBAR,
        "estado_anterior": PENDIENTE,
        "estado_nuevo": APROBADA,
        "motivo": motivo,
        "id_operador": 7,
        "fecha": fecha,
    }
    datos.update(cambios)
    return EventoHabilitacion(**datos)


def alta():
    return evento(
        "Alta",
        accion=AccionHabilitacion.ALTA,
        estado_anterior=None,
        estado_nuevo=PENDIENTE,
        id_operador=None,
    )


@POR_ENTIDAD
def test_el_historial_confirmado_devuelve_el_evento_con_todos_sus_campos(
    repositorio, entidades, sesion_bd, fabrica_sesiones, registrar, historial
):
    en_otra_zona = datetime(2026, 6, 15, 9, 30, 45, 123456, tzinfo=timezone(timedelta(hours=-3)))
    original = evento(fecha=en_otra_zona)
    getattr(repositorio, registrar)(1, original)
    sesion_bd.commit()

    with fabrica_sesiones() as otra_sesion:
        [leido] = getattr(SqlRepositorioHabilitaciones(otra_sesion), historial)(1)

    assert isinstance(leido, EventoHabilitacion)
    assert leido.accion is AccionHabilitacion.APROBAR
    assert leido.estado_anterior is PENDIENTE
    assert leido.estado_nuevo is APROBADA
    assert leido.motivo == "Documentacion revisada"
    assert leido.id_operador == 7
    assert leido.fecha == original.fecha  # mismo instante, con microsegundos
    assert leido.fecha.utcoffset() == timedelta(0)  # aware y en UTC


@POR_ENTIDAD
def test_el_evento_de_alta_con_valores_nulos_hace_ida_y_vuelta(
    repositorio, entidades, sesion_bd, fabrica_sesiones, registrar, historial
):
    getattr(repositorio, registrar)(1, alta())
    sesion_bd.commit()

    with fabrica_sesiones() as otra_sesion:
        [leido] = getattr(SqlRepositorioHabilitaciones(otra_sesion), historial)(1)

    assert leido.accion is AccionHabilitacion.ALTA
    assert leido.estado_anterior is None
    assert leido.estado_nuevo is PENDIENTE
    assert leido.id_operador is None
    assert leido.fecha == FECHA


@POR_ENTIDAD
def test_el_historial_va_en_orden_de_registro_aunque_las_fechas_no_lo_esten(
    repositorio, entidades, registrar, historial
):
    tercero_en_fecha = evento("Primero registrado", fecha=FECHA + timedelta(days=2))
    primero_en_fecha = evento("Segundo registrado", fecha=FECHA)
    medio_en_fecha = evento("Tercero registrado", fecha=FECHA + timedelta(days=1))
    for e in (tercero_en_fecha, primero_en_fecha, medio_en_fecha):
        getattr(repositorio, registrar)(1, e)

    motivos = [e.motivo for e in getattr(repositorio, historial)(1)]

    assert motivos == ["Primero registrado", "Segundo registrado", "Tercero registrado"]


def test_los_historiales_de_conductor_y_de_vehiculo_son_independientes_con_el_mismo_id(
    repositorio, entidades
):
    repositorio.registrar_evento_conductor(1, evento("Del conductor 1"))
    repositorio.registrar_evento_vehiculo(1, evento("Del vehiculo 1"))

    assert [e.motivo for e in repositorio.historial_conductor(1)] == ["Del conductor 1"]
    assert [e.motivo for e in repositorio.historial_vehiculo(1)] == ["Del vehiculo 1"]


@POR_ENTIDAD
def test_el_historial_de_una_entidad_no_se_mezcla_con_el_de_otra_del_mismo_tipo(
    repositorio, entidades, registrar, historial
):
    getattr(repositorio, registrar)(1, evento("De la entidad 1"))
    getattr(repositorio, registrar)(2, evento("De la entidad 2"))

    assert [e.motivo for e in getattr(repositorio, historial)(1)] == ["De la entidad 1"]
    assert [e.motivo for e in getattr(repositorio, historial)(2)] == ["De la entidad 2"]


@POR_ENTIDAD
def test_historial_sin_eventos_o_de_una_entidad_inexistente_es_una_lista_vacia(
    repositorio, entidades, registrar, historial
):
    getattr(repositorio, registrar)(1, evento())

    assert getattr(repositorio, historial)(2) == []
    assert getattr(repositorio, historial)(999) == []


def test_el_repositorio_no_ofrece_operaciones_de_actualizar_ni_borrar(repositorio):
    publicos = {
        nombre
        for nombre in dir(repositorio)
        if not nombre.startswith("_") and callable(getattr(repositorio, nombre))
    }

    assert publicos == METODOS_PUBLICOS_DEL_PUERTO


def test_registrar_un_evento_no_modifica_el_estado_de_la_entidad(repositorio, entidades, sesion_bd):
    repositorio.registrar_evento_conductor(1, evento())  # APROBAR: PENDIENTE -> APROBADA
    repositorio.registrar_evento_vehiculo(1, evento())

    estado_conductor = sesion_bd.execute(
        text("SELECT estado_habilitacion FROM conductor WHERE id_conductor = 1")
    ).scalar_one()
    estado_vehiculo = sesion_bd.execute(
        text("SELECT estado_habilitacion FROM vehiculo WHERE id_vehiculo = 1")
    ).scalar_one()

    assert estado_conductor == "PENDIENTE"
    assert estado_vehiculo == "PENDIENTE"


@POR_ENTIDAD
@pytest.mark.parametrize("motivo", ["", "   "], ids=["vacio", "solo_espacios"])
def test_un_motivo_vacio_viola_el_check_y_la_sesion_sigue_usable(
    repositorio, entidades, registrar, historial, motivo
):
    with pytest.raises(IntegrityError):
        getattr(repositorio, registrar)(1, evento(motivo))

    getattr(repositorio, registrar)(1, evento("Motivo valido"))  # sin rollback manual
    assert [e.motivo for e in getattr(repositorio, historial)(1)] == ["Motivo valido"]


@POR_ENTIDAD
def test_registrar_para_una_entidad_inexistente_propaga_el_integrity_error_de_la_fk(
    repositorio, entidades, registrar, historial
):
    with pytest.raises(IntegrityError):
        getattr(repositorio, registrar)(999, evento())

    assert getattr(repositorio, historial)(999) == []
    getattr(repositorio, registrar)(1, evento())  # la sesion sigue usable
    assert len(getattr(repositorio, historial)(1)) == 1
