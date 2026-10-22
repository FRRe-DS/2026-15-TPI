"""Contrato de los fakes en memoria que usan los tests de los casos de uso.

Los fakes se comportan como los repositorios SQL (T034-T039) frente a los puertos:
- Punto de entrada: `UnidadDeTrabajoEnMemoria()`, que expone `conductores`, `vehiculos`,
  `documentos` y `habilitaciones`. Los cuatro comparten el mismo estado, asi que
  `conductores.listar(tipo_vehiculo=...)` ve los vehiculos guardados en `vehiculos`.
- Los repositorios funcionan con o sin `with uow:`.
- `guardar` es un alta si la entidad no tiene id y una actualizacion si ya lo tiene
  (los casos de uso cambian el estado de habilitacion y vuelven a llamar a `guardar`).
- El vehiculo se asocia a su conductor con `vehiculo.id_conductor` antes de `guardar`.
- Transaccion: el estado confirmado arranca vacio; `commit()` confirma el estado actual;
  `rollback()` y salir del `with` sin `commit()` (o con una excepcion) vuelven al ultimo
  estado confirmado, como hace la base.
- `RelojFijo(ahora)` devuelve siempre ese instante hasta que se lo avanza.
"""

from datetime import UTC, date, datetime

import pytest
from app.aplicacion.puertos.reloj import Reloj
from app.aplicacion.puertos.repositorio_conductores import RepositorioConductores
from app.aplicacion.puertos.repositorio_documentos import RepositorioDocumentos
from app.aplicacion.puertos.repositorio_habilitaciones import (
    RepositorioHabilitaciones,
)
from app.aplicacion.puertos.repositorio_vehiculos import RepositorioVehiculos
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.conductor import Conductor
from app.dominio.documento import Documento, TipoDocumento
from app.dominio.errores import DniDuplicado, PatenteDuplicada
from app.dominio.habilitacion import (
    AccionHabilitacion,
    EstadoHabilitacion,
    EventoHabilitacion,
)
from app.dominio.vehiculo import TipoServicio, TipoVehiculo, Vehiculo

from tests.unitarios.fakes.reloj_fijo import RelojFijo
from tests.unitarios.fakes.repositorios_en_memoria import UnidadDeTrabajoEnMemoria

AHORA = datetime(2026, 6, 15, 23, 30, tzinfo=UTC)


@pytest.fixture
def uow():
    return UnidadDeTrabajoEnMemoria()


def nuevo_conductor(dni="30123456", **estado):
    conductor = Conductor.crear(
        dni=dni,
        nombre="Ana",
        apellido="Perez",
        telefono="+54 379 4000000",
        email="ana@example.com",
    )
    for atributo, valor in estado.items():
        setattr(conductor, atributo, valor)
    return conductor


def nuevo_vehiculo(id_conductor, patente="AB123CD", tipo=TipoVehiculo.AUTO, **estado):
    vehiculo = Vehiculo.crear(
        tipo=tipo,
        patente=patente,
        marca="Toyota",
        modelo="Etios",
        anio=2019,
        tipos_servicio=[TipoServicio.PASAJEROS],
    )
    vehiculo.id_conductor = id_conductor
    for atributo, valor in estado.items():
        setattr(vehiculo, atributo, valor)
    return vehiculo


def nueva_licencia(numero="LIC-1"):
    return Documento.crear(
        tipo=TipoDocumento.LICENCIA,
        numero=numero,
        categoria="B1",
        fecha_emision=date(2024, 1, 10),
        fecha_vencimiento=date(2029, 1, 10),
        url_archivo="https://almacen.example.com/licencias/lic.pdf",
    )


def nuevo_evento(motivo="Documentacion revisada"):
    return EventoHabilitacion(
        accion=AccionHabilitacion.APROBAR,
        estado_anterior=EstadoHabilitacion.PENDIENTE,
        estado_nuevo=EstadoHabilitacion.APROBADA,
        motivo=motivo,
        id_operador=7,
        fecha=AHORA,
    )


def dnis(conductores):
    return [conductor.dni for conductor in conductores]


def patentes(vehiculos):
    return [vehiculo.patente for vehiculo in vehiculos]


# --- La unidad de trabajo expone repositorios que implementan los puertos ---


def test_la_unidad_de_trabajo_expone_repositorios_que_implementan_los_puertos(uow):
    assert isinstance(uow, UnidadDeTrabajo)
    assert isinstance(uow.conductores, RepositorioConductores)
    assert isinstance(uow.vehiculos, RepositorioVehiculos)
    assert isinstance(uow.documentos, RepositorioDocumentos)
    assert isinstance(uow.habilitaciones, RepositorioHabilitaciones)


def test_entrar_al_with_devuelve_la_misma_unidad_de_trabajo(uow):
    with uow as unidad:
        assert unidad is uow


# --- Conductores ---


def test_guardar_conductor_asigna_ids_incrementales(uow):
    primero = uow.conductores.guardar(nuevo_conductor(dni="30000001"))
    segundo = uow.conductores.guardar(nuevo_conductor(dni="30000002"))

    assert primero.id is not None
    assert segundo.id == primero.id + 1


def test_obtener_conductor_devuelve_el_guardado(uow):
    guardado = uow.conductores.guardar(nuevo_conductor(dni="30000001"))

    assert uow.conductores.obtener(guardado.id).dni == "30000001"


def test_obtener_conductor_inexistente_devuelve_none(uow):
    assert uow.conductores.obtener(999) is None


def test_guardar_conductor_con_dni_existente_lanza_dni_duplicado(uow):
    uow.conductores.guardar(nuevo_conductor(dni="30000001"))

    with pytest.raises(DniDuplicado):
        uow.conductores.guardar(nuevo_conductor(dni="30000001"))


def test_guardar_de_nuevo_un_conductor_existente_lo_actualiza_sin_duplicar(uow):
    conductor = uow.conductores.guardar(nuevo_conductor(dni="30000001"))
    conductor.habilitacion = EstadoHabilitacion.APROBADA

    actualizado = uow.conductores.guardar(conductor)

    assert actualizado.id == conductor.id
    assert uow.conductores.obtener(conductor.id).habilitacion is (EstadoHabilitacion.APROBADA)
    assert len(uow.conductores.listar()) == 1


def test_listar_conductores_sin_filtros_devuelve_todos_en_orden_de_alta(uow):
    for dni in ("30000001", "30000002", "30000003"):
        uow.conductores.guardar(nuevo_conductor(dni=dni))

    assert dnis(uow.conductores.listar()) == ["30000001", "30000002", "30000003"]


def test_listar_conductores_habilitado_verdadero_devuelve_solo_los_aprobados(uow):
    uow.conductores.guardar(
        nuevo_conductor(dni="30000001", habilitacion=EstadoHabilitacion.APROBADA)
    )
    for dni, estado in [
        ("30000002", EstadoHabilitacion.PENDIENTE),
        ("30000003", EstadoHabilitacion.OBSERVADA),
        ("30000004", EstadoHabilitacion.SUSPENDIDA),
        ("30000005", EstadoHabilitacion.RECHAZADA),
    ]:
        uow.conductores.guardar(nuevo_conductor(dni=dni, habilitacion=estado))

    assert dnis(uow.conductores.listar(habilitado=True)) == ["30000001"]


def test_listar_conductores_habilitado_falso_devuelve_los_que_no_estan_aprobados(uow):
    uow.conductores.guardar(
        nuevo_conductor(dni="30000001", habilitacion=EstadoHabilitacion.APROBADA)
    )
    for dni, estado in [
        ("30000002", EstadoHabilitacion.PENDIENTE),
        ("30000003", EstadoHabilitacion.OBSERVADA),
        ("30000004", EstadoHabilitacion.SUSPENDIDA),
        ("30000005", EstadoHabilitacion.RECHAZADA),
    ]:
        uow.conductores.guardar(nuevo_conductor(dni=dni, habilitacion=estado))

    assert dnis(uow.conductores.listar(habilitado=False)) == [
        "30000002",
        "30000003",
        "30000004",
        "30000005",
    ]


@pytest.mark.parametrize(
    ("disponible", "dnis_esperados"),
    [(True, ["30000001"]), (False, ["30000002"])],
)
def test_listar_conductores_filtra_por_disponible(uow, disponible, dnis_esperados):
    uow.conductores.guardar(nuevo_conductor(dni="30000001", disponible=True))
    uow.conductores.guardar(nuevo_conductor(dni="30000002", disponible=False))

    assert dnis(uow.conductores.listar(disponible=disponible)) == dnis_esperados


def test_listar_conductores_filtra_por_tipo_de_vehiculo_con_al_menos_uno_de_ese_tipo(
    uow,
):
    con_auto = uow.conductores.guardar(nuevo_conductor(dni="30000001"))
    con_moto = uow.conductores.guardar(nuevo_conductor(dni="30000002"))
    con_ambos = uow.conductores.guardar(nuevo_conductor(dni="30000003"))
    uow.conductores.guardar(nuevo_conductor(dni="30000004"))  # sin vehiculos
    uow.vehiculos.guardar(nuevo_vehiculo(con_auto.id, "AAA111", TipoVehiculo.AUTO))
    uow.vehiculos.guardar(nuevo_vehiculo(con_moto.id, "BBB222", TipoVehiculo.MOTO))
    uow.vehiculos.guardar(nuevo_vehiculo(con_ambos.id, "CCC333", TipoVehiculo.AUTO))
    uow.vehiculos.guardar(nuevo_vehiculo(con_ambos.id, "DDD444", TipoVehiculo.MOTO))

    assert dnis(uow.conductores.listar(tipo_vehiculo=TipoVehiculo.AUTO)) == [
        "30000001",
        "30000003",
    ]
    assert dnis(uow.conductores.listar(tipo_vehiculo=TipoVehiculo.MOTO)) == [
        "30000002",
        "30000003",
    ]


def test_listar_conductores_combina_los_filtros(uow):
    aprobado_disponible = uow.conductores.guardar(
        nuevo_conductor(dni="30000001", habilitacion=EstadoHabilitacion.APROBADA, disponible=True)
    )
    aprobado_no_disponible = uow.conductores.guardar(
        nuevo_conductor(dni="30000002", habilitacion=EstadoHabilitacion.APROBADA, disponible=False)
    )
    pendiente_disponible = uow.conductores.guardar(nuevo_conductor(dni="30000003", disponible=True))
    for conductor, patente in [
        (aprobado_disponible, "AAA111"),
        (aprobado_no_disponible, "BBB222"),
        (pendiente_disponible, "CCC333"),
    ]:
        uow.vehiculos.guardar(nuevo_vehiculo(conductor.id, patente))

    resultado = uow.conductores.listar(
        habilitado=True, disponible=True, tipo_vehiculo=TipoVehiculo.AUTO
    )

    assert dnis(resultado) == ["30000001"]


# --- Vehiculos ---


def test_guardar_vehiculo_asigna_ids_incrementales(uow):
    conductor = uow.conductores.guardar(nuevo_conductor())

    primero = uow.vehiculos.guardar(nuevo_vehiculo(conductor.id, "AAA111"))
    segundo = uow.vehiculos.guardar(nuevo_vehiculo(conductor.id, "BBB222"))

    assert primero.id is not None
    assert segundo.id == primero.id + 1


def test_obtener_vehiculo_devuelve_el_guardado_del_conductor(uow):
    conductor = uow.conductores.guardar(nuevo_conductor())
    guardado = uow.vehiculos.guardar(nuevo_vehiculo(conductor.id, "AAA111"))

    assert uow.vehiculos.obtener(conductor.id, guardado.id).patente == "AAA111"


def test_obtener_vehiculo_inexistente_devuelve_none(uow):
    conductor = uow.conductores.guardar(nuevo_conductor())

    assert uow.vehiculos.obtener(conductor.id, 999) is None


def test_obtener_vehiculo_de_otro_conductor_devuelve_none(uow):
    duenio = uow.conductores.guardar(nuevo_conductor(dni="30000001"))
    otro = uow.conductores.guardar(nuevo_conductor(dni="30000002"))
    vehiculo = uow.vehiculos.guardar(nuevo_vehiculo(duenio.id, "AAA111"))

    assert uow.vehiculos.obtener(otro.id, vehiculo.id) is None


def test_guardar_vehiculo_con_patente_existente_lanza_patente_duplicada(uow):
    uno = uow.conductores.guardar(nuevo_conductor(dni="30000001"))
    otro = uow.conductores.guardar(nuevo_conductor(dni="30000002"))
    uow.vehiculos.guardar(nuevo_vehiculo(uno.id, "AAA111"))

    with pytest.raises(PatenteDuplicada):
        uow.vehiculos.guardar(nuevo_vehiculo(otro.id, "AAA111"))


def test_guardar_de_nuevo_un_vehiculo_existente_lo_actualiza_sin_duplicar(uow):
    conductor = uow.conductores.guardar(nuevo_conductor())
    vehiculo = uow.vehiculos.guardar(nuevo_vehiculo(conductor.id, "AAA111"))
    vehiculo.habilitacion = EstadoHabilitacion.APROBADA

    actualizado = uow.vehiculos.guardar(vehiculo)

    assert actualizado.id == vehiculo.id
    assert uow.vehiculos.obtener(conductor.id, vehiculo.id).habilitacion is (
        EstadoHabilitacion.APROBADA
    )
    assert len(uow.vehiculos.listar_por_conductor(conductor.id)) == 1


def test_listar_vehiculos_devuelve_solo_los_del_conductor_en_orden_de_alta(uow):
    uno = uow.conductores.guardar(nuevo_conductor(dni="30000001"))
    otro = uow.conductores.guardar(nuevo_conductor(dni="30000002"))
    uow.vehiculos.guardar(nuevo_vehiculo(uno.id, "AAA111"))
    uow.vehiculos.guardar(nuevo_vehiculo(otro.id, "BBB222"))
    uow.vehiculos.guardar(nuevo_vehiculo(uno.id, "CCC333"))

    assert patentes(uow.vehiculos.listar_por_conductor(uno.id)) == ["AAA111", "CCC333"]


def test_listar_vehiculos_de_un_conductor_sin_vehiculos_devuelve_lista_vacia(uow):
    conductor = uow.conductores.guardar(nuevo_conductor())

    assert uow.vehiculos.listar_por_conductor(conductor.id) == []


def test_listar_vehiculos_filtra_por_tipo_y_por_habilitacion(uow):
    conductor = uow.conductores.guardar(nuevo_conductor())
    uow.vehiculos.guardar(nuevo_vehiculo(conductor.id, "AAA111", TipoVehiculo.AUTO))
    uow.vehiculos.guardar(
        nuevo_vehiculo(
            conductor.id,
            "BBB222",
            TipoVehiculo.AUTO,
            habilitacion=EstadoHabilitacion.APROBADA,
        )
    )
    uow.vehiculos.guardar(
        nuevo_vehiculo(
            conductor.id,
            "CCC333",
            TipoVehiculo.MOTO,
            habilitacion=EstadoHabilitacion.APROBADA,
        )
    )

    por_tipo = uow.vehiculos.listar_por_conductor(conductor.id, tipo=TipoVehiculo.MOTO)
    por_habilitacion = uow.vehiculos.listar_por_conductor(
        conductor.id, habilitacion=EstadoHabilitacion.APROBADA
    )
    por_ambos = uow.vehiculos.listar_por_conductor(
        conductor.id, tipo=TipoVehiculo.AUTO, habilitacion=EstadoHabilitacion.APROBADA
    )

    assert patentes(por_tipo) == ["CCC333"]
    assert patentes(por_habilitacion) == ["BBB222", "CCC333"]
    assert patentes(por_ambos) == ["BBB222"]


# --- Documentos ---


def test_guardar_documento_asigna_ids_incrementales(uow):
    conductor = uow.conductores.guardar(nuevo_conductor())

    primero = uow.documentos.guardar(conductor.id, nueva_licencia("LIC-1"))
    segundo = uow.documentos.guardar(conductor.id, nueva_licencia("LIC-2"))

    assert primero.id is not None
    assert segundo.id == primero.id + 1


def test_listar_documentos_devuelve_solo_los_del_conductor_en_orden_de_alta(uow):
    uno = uow.conductores.guardar(nuevo_conductor(dni="30000001"))
    otro = uow.conductores.guardar(nuevo_conductor(dni="30000002"))
    uow.documentos.guardar(uno.id, nueva_licencia("LIC-1"))
    uow.documentos.guardar(otro.id, nueva_licencia("LIC-2"))
    uow.documentos.guardar(uno.id, nueva_licencia("LIC-3"))

    numeros = [d.numero for d in uow.documentos.listar_por_conductor(uno.id)]

    assert numeros == ["LIC-1", "LIC-3"]


def test_listar_documentos_de_un_conductor_sin_documentos_devuelve_lista_vacia(uow):
    conductor = uow.conductores.guardar(nuevo_conductor())

    assert uow.documentos.listar_por_conductor(conductor.id) == []


# --- Historial de habilitacion ---


def test_historial_del_conductor_devuelve_sus_eventos_en_orden_de_registro(uow):
    primero = nuevo_evento("Primero")
    segundo = nuevo_evento("Segundo")
    uow.habilitaciones.registrar_evento_conductor(1, primero)
    uow.habilitaciones.registrar_evento_conductor(2, nuevo_evento("De otro conductor"))
    uow.habilitaciones.registrar_evento_conductor(1, segundo)

    assert uow.habilitaciones.historial_conductor(1) == [primero, segundo]


def test_historial_del_vehiculo_devuelve_sus_eventos_en_orden_de_registro(uow):
    primero = nuevo_evento("Primero")
    segundo = nuevo_evento("Segundo")
    uow.habilitaciones.registrar_evento_vehiculo(1, primero)
    uow.habilitaciones.registrar_evento_vehiculo(2, nuevo_evento("De otro vehiculo"))
    uow.habilitaciones.registrar_evento_vehiculo(1, segundo)

    assert uow.habilitaciones.historial_vehiculo(1) == [primero, segundo]


def test_el_historial_del_conductor_y_el_del_vehiculo_son_independientes(uow):
    uow.habilitaciones.registrar_evento_conductor(1, nuevo_evento("Del conductor"))

    assert uow.habilitaciones.historial_vehiculo(1) == []


def test_historial_sin_eventos_devuelve_lista_vacia(uow):
    assert uow.habilitaciones.historial_conductor(1) == []
    assert uow.habilitaciones.historial_vehiculo(1) == []


# --- Unidad de trabajo: bloqueo y transaccion ---


def test_bloquear_conductor_devuelve_el_conductor_o_none(uow):
    guardado = uow.conductores.guardar(nuevo_conductor(dni="30000001"))

    assert uow.bloquear_conductor(guardado.id).dni == "30000001"
    assert uow.bloquear_conductor(999) is None


def test_bloquear_vehiculo_devuelve_el_vehiculo_solo_si_es_del_conductor(uow):
    duenio = uow.conductores.guardar(nuevo_conductor(dni="30000001"))
    otro = uow.conductores.guardar(nuevo_conductor(dni="30000002"))
    vehiculo = uow.vehiculos.guardar(nuevo_vehiculo(duenio.id, "AAA111"))

    assert uow.bloquear_vehiculo(duenio.id, vehiculo.id).patente == "AAA111"
    assert uow.bloquear_vehiculo(otro.id, vehiculo.id) is None
    assert uow.bloquear_vehiculo(duenio.id, 999) is None


def test_commit_confirma_los_cambios_y_un_rollback_posterior_no_los_deshace(uow):
    with uow:
        conductor = uow.conductores.guardar(nuevo_conductor())
        uow.commit()
        uow.rollback()

    assert uow.conductores.obtener(conductor.id) is not None


def test_rollback_descarta_los_altas_no_confirmadas(uow):
    confirmado = uow.conductores.guardar(nuevo_conductor(dni="30000001"))
    uow.commit()
    sin_confirmar = uow.conductores.guardar(nuevo_conductor(dni="30000002"))

    uow.rollback()

    assert uow.conductores.obtener(confirmado.id) is not None
    assert uow.conductores.obtener(sin_confirmar.id) is None


def test_rollback_deshace_las_modificaciones_no_confirmadas(uow):
    conductor = uow.conductores.guardar(nuevo_conductor())
    uow.commit()
    conductor.habilitacion = EstadoHabilitacion.APROBADA
    uow.conductores.guardar(conductor)
    uow.habilitaciones.registrar_evento_conductor(conductor.id, nuevo_evento())

    uow.rollback()

    assert uow.conductores.obtener(conductor.id).habilitacion is (EstadoHabilitacion.PENDIENTE)
    assert uow.habilitaciones.historial_conductor(conductor.id) == []


def test_salir_del_with_con_una_excepcion_descarta_lo_no_confirmado(uow):
    with pytest.raises(RuntimeError), uow:
        uow.conductores.guardar(nuevo_conductor())
        raise RuntimeError("falla a mitad de la transaccion")

    assert uow.conductores.listar() == []


def test_salir_del_with_sin_commit_descarta_lo_no_confirmado(uow):
    with uow:
        uow.conductores.guardar(nuevo_conductor())

    assert uow.conductores.listar() == []


def test_salir_del_with_despues_de_commit_conserva_los_cambios(uow):
    with uow:
        uow.conductores.guardar(nuevo_conductor())
        uow.commit()

    assert len(uow.conductores.listar()) == 1


# --- Reloj fijo ---


def test_el_reloj_fijo_implementa_el_puerto_y_devuelve_siempre_el_mismo_instante():
    reloj = RelojFijo(AHORA)

    assert isinstance(reloj, Reloj)
    assert reloj.ahora() == AHORA
    assert reloj.ahora() == AHORA


def test_el_reloj_fijo_devuelve_la_fecha_de_hoy():
    assert RelojFijo(AHORA).hoy() == date(2026, 6, 15)


def test_avanzar_dias_mueve_ahora_y_hoy():
    reloj = RelojFijo(AHORA)

    reloj.avanzar(dias=3)

    assert reloj.ahora() == datetime(2026, 6, 18, 23, 30, tzinfo=UTC)
    assert reloj.hoy() == date(2026, 6, 18)


def test_avanzar_un_dia_cruza_el_cambio_de_fecha():
    reloj = RelojFijo(datetime(2026, 6, 30, 23, 59, tzinfo=UTC))

    reloj.avanzar(dias=1)

    assert reloj.hoy() == date(2026, 7, 1)
