"""`SqlRepositorioConductores(session)`: el puerto `RepositorioConductores` sobre PostgreSQL.

Se comporta como el fake `RepositorioConductoresEnMemoria` (ver `tests/unitarios/fakes`):
- `guardar` sin id inserta y devuelve el conductor de dominio con id asignado (1, 2, ...);
  con id actualiza la fila y conserva el id. Hace `flush`, no `commit`: confirmar es
  trabajo de la unidad de trabajo, asi que los tests llaman a `sesion_bd.commit()`.
- `DniDuplicado` sale del `IntegrityError` de `uq_conductor_dni` (no se consulta antes de
  insertar, para no tener una carrera entre la consulta y el INSERT); el INSERT se aisla
  para que la sesion siga siendo usable despues del error. Cualquier otro
  `IntegrityError` se propaga sin traducir.
- `listar` ordena por id y filtra por `habilitado` (True solo APROBADA), `disponible` y
  `tipo_vehiculo` (al menos un vehiculo de ese tipo, sin duplicar al conductor), con AND.
- `test_guardar_un_conductor_con_id_inexistente_lanza_no_encontrado` es un test de
  CARACTERIZACION: fija una decision tomada en la implementacion (los ids los genera la
  base, un id que no existe no es un alta) y pasa de entrada, sin fase Red.
"""

import pytest
from app.dominio.conductor import Conductor
from app.dominio.errores import DniDuplicado, NoEncontrado
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.vehiculo import TipoVehiculo
from app.infraestructura.db.modelos import Vehiculo as VehiculoOrm
from app.infraestructura.repositorios.sql_conductores import SqlRepositorioConductores
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

PENDIENTE = EstadoHabilitacion.PENDIENTE
APROBADA = EstadoHabilitacion.APROBADA
AUTO = TipoVehiculo.AUTO
MOTO = TipoVehiculo.MOTO


@pytest.fixture
def repositorio(sesion_bd):
    return SqlRepositorioConductores(sesion_bd)


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


def sembrar_vehiculo(sesion, id_conductor, patente, tipo):
    sesion.add(
        VehiculoOrm(
            id_conductor=id_conductor,
            patente=patente,
            marca="Toyota",
            modelo="Etios",
            anio=2019,
            tipo=tipo.value,
        )
    )
    sesion.flush()


def dnis(conductores):
    return [conductor.dni for conductor in conductores]


# --- guardar y obtener ---


def test_guardar_conductor_nuevo_devuelve_el_conductor_de_dominio_con_ids_incrementales(
    repositorio,
):
    primero = repositorio.guardar(nuevo_conductor("30000001"))
    segundo = repositorio.guardar(nuevo_conductor("30000002"))

    assert isinstance(primero, Conductor)
    assert (primero.id, segundo.id) == (1, 2)
    assert primero.dni == "30000001"


def test_el_conductor_confirmado_se_lee_con_todos_sus_campos_desde_otra_sesion(
    repositorio, sesion_bd, fabrica_sesiones
):
    conductor = nuevo_conductor(
        "30123456", habilitacion=EstadoHabilitacion.OBSERVADA, conectado=True, disponible=True
    )
    guardado = repositorio.guardar(conductor)
    sesion_bd.commit()

    with fabrica_sesiones() as otra_sesion:
        leido = SqlRepositorioConductores(otra_sesion).obtener(guardado.id)

    assert isinstance(leido, Conductor)
    assert leido.id == guardado.id
    assert leido.dni == "30123456"
    assert leido.nombre == "Ana"
    assert leido.apellido == "Perez"
    assert leido.telefono == "+54 379 4000000"
    assert leido.email == "ana@example.com"
    assert leido.habilitacion is EstadoHabilitacion.OBSERVADA
    assert leido.conectado is True
    assert leido.disponible is True


def test_obtener_conductor_inexistente_devuelve_none(repositorio):
    repositorio.guardar(nuevo_conductor())

    assert repositorio.obtener(999) is None


def test_guardar_un_conductor_con_id_lo_actualiza_conservando_el_id(
    repositorio, sesion_bd, fabrica_sesiones
):
    conductor = repositorio.guardar(nuevo_conductor())
    sesion_bd.commit()
    conductor.habilitacion = APROBADA
    conductor.conectado = True
    conductor.disponible = True

    actualizado = repositorio.guardar(conductor)
    sesion_bd.commit()

    assert actualizado.id == conductor.id
    with fabrica_sesiones() as otra_sesion:
        repositorio_otra = SqlRepositorioConductores(otra_sesion)
        leido = repositorio_otra.obtener(conductor.id)
        assert leido.habilitacion is APROBADA
        assert leido.conectado is True
        assert leido.disponible is True
        assert len(repositorio_otra.listar()) == 1


def test_guardar_un_conductor_con_id_inexistente_lanza_no_encontrado(repositorio):
    """Caracterizacion: el comportamiento ya existia cuando se escribio este test."""
    conductor = nuevo_conductor()
    conductor.id = 999

    with pytest.raises(NoEncontrado):
        repositorio.guardar(conductor)

    assert repositorio.listar() == []


# --- DniDuplicado ---


def test_guardar_con_dni_existente_lanza_dni_duplicado(repositorio):
    repositorio.guardar(nuevo_conductor("30000001"))

    with pytest.raises(DniDuplicado):
        repositorio.guardar(nuevo_conductor("30000001"))


def test_la_sesion_sigue_usable_despues_de_un_dni_duplicado(
    repositorio, sesion_bd, fabrica_sesiones
):
    original = repositorio.guardar(nuevo_conductor("30000001"))

    with pytest.raises(DniDuplicado):
        repositorio.guardar(nuevo_conductor("30000001"))

    assert repositorio.obtener(original.id).dni == "30000001"  # sin rollback manual
    sesion_bd.commit()
    with fabrica_sesiones() as otra_sesion:
        assert dnis(SqlRepositorioConductores(otra_sesion).listar()) == ["30000001"]


def test_el_dni_duplicado_se_detecta_con_el_insert_y_no_con_una_consulta_previa(
    repositorio, sesion_bd
):
    repositorio.guardar(nuevo_conductor("30000001"))
    sentencias = []

    def registrar(conexion, cursor, sentencia, parametros, contexto, ejecutar_muchos):
        sentencias.append(sentencia.lstrip().upper())

    motor = sesion_bd.get_bind()
    event.listen(motor, "before_cursor_execute", registrar)
    try:
        with pytest.raises(DniDuplicado):
            repositorio.guardar(nuevo_conductor("30000001"))
    finally:
        event.remove(motor, "before_cursor_execute", registrar)

    assert any(sentencia.startswith("INSERT") for sentencia in sentencias)
    assert not any(sentencia.startswith("SELECT") for sentencia in sentencias)


def test_un_integrity_error_que_no_es_de_dni_no_se_traduce_a_dni_duplicado(repositorio):
    con_email_invalido = Conductor(
        dni="30000001",
        nombre="Ana",
        apellido="Perez",
        telefono="+54 379 4000000",
        email="sin-arroba",  # viola ck_conductor_email_formato
    )

    with pytest.raises(IntegrityError):
        repositorio.guardar(con_email_invalido)


# --- listar ---


def test_listar_sin_conductores_devuelve_lista_vacia(repositorio):
    assert repositorio.listar() == []


def test_listar_sin_filtros_devuelve_todos_en_orden_de_id(repositorio):
    for dni in ("30000003", "30000001", "30000002"):
        repositorio.guardar(nuevo_conductor(dni))

    resultado = repositorio.listar()

    assert dnis(resultado) == ["30000003", "30000001", "30000002"]
    assert [c.id for c in resultado] == [1, 2, 3]
    assert all(isinstance(c, Conductor) for c in resultado)


def test_listar_habilitado_verdadero_devuelve_solo_los_aprobados(repositorio):
    repositorio.guardar(nuevo_conductor("30000001", habilitacion=APROBADA))
    for dni, estado in [
        ("30000002", PENDIENTE),
        ("30000003", EstadoHabilitacion.OBSERVADA),
        ("30000004", EstadoHabilitacion.SUSPENDIDA),
        ("30000005", EstadoHabilitacion.RECHAZADA),
    ]:
        repositorio.guardar(nuevo_conductor(dni, habilitacion=estado))

    resultado = repositorio.listar(habilitado=True)

    assert dnis(resultado) == ["30000001"]
    assert resultado[0].habilitacion is APROBADA


def test_listar_habilitado_falso_devuelve_los_que_no_estan_aprobados(repositorio):
    repositorio.guardar(nuevo_conductor("30000001", habilitacion=APROBADA))
    for dni, estado in [
        ("30000002", PENDIENTE),
        ("30000003", EstadoHabilitacion.OBSERVADA),
        ("30000004", EstadoHabilitacion.SUSPENDIDA),
        ("30000005", EstadoHabilitacion.RECHAZADA),
    ]:
        repositorio.guardar(nuevo_conductor(dni, habilitacion=estado))

    assert dnis(repositorio.listar(habilitado=False)) == [
        "30000002",
        "30000003",
        "30000004",
        "30000005",
    ]


@pytest.mark.parametrize(
    ("disponible", "dnis_esperados"),
    [(True, ["30000001"]), (False, ["30000002"])],
)
def test_listar_filtra_por_disponible(repositorio, disponible, dnis_esperados):
    repositorio.guardar(nuevo_conductor("30000001", disponible=True))
    repositorio.guardar(nuevo_conductor("30000002", disponible=False))

    assert dnis(repositorio.listar(disponible=disponible)) == dnis_esperados


def test_listar_filtra_por_tipo_de_vehiculo_sin_duplicar_conductores(repositorio, sesion_bd):
    con_auto = repositorio.guardar(nuevo_conductor("30000001"))
    con_moto = repositorio.guardar(nuevo_conductor("30000002"))
    con_ambos = repositorio.guardar(nuevo_conductor("30000003"))
    con_dos_autos = repositorio.guardar(nuevo_conductor("30000004"))
    repositorio.guardar(nuevo_conductor("30000005"))  # sin vehiculos
    sembrar_vehiculo(sesion_bd, con_auto.id, "AAA111", AUTO)
    sembrar_vehiculo(sesion_bd, con_moto.id, "BBB222", MOTO)
    sembrar_vehiculo(sesion_bd, con_ambos.id, "CCC333", AUTO)
    sembrar_vehiculo(sesion_bd, con_ambos.id, "DDD444", MOTO)
    sembrar_vehiculo(sesion_bd, con_dos_autos.id, "EEE555", AUTO)
    sembrar_vehiculo(sesion_bd, con_dos_autos.id, "FFF666", AUTO)

    assert dnis(repositorio.listar(tipo_vehiculo=AUTO)) == [
        "30000001",
        "30000003",
        "30000004",
    ]
    assert dnis(repositorio.listar(tipo_vehiculo=MOTO)) == ["30000002", "30000003"]


def test_listar_combina_los_filtros_con_and(repositorio, sesion_bd):
    cumple_todo = repositorio.guardar(
        nuevo_conductor("30000001", habilitacion=APROBADA, disponible=True)
    )
    no_disponible = repositorio.guardar(
        nuevo_conductor("30000002", habilitacion=APROBADA, disponible=False)
    )
    no_aprobado = repositorio.guardar(nuevo_conductor("30000003", disponible=True))
    sin_el_tipo = repositorio.guardar(
        nuevo_conductor("30000004", habilitacion=APROBADA, disponible=True)
    )
    for conductor, patente in [
        (cumple_todo, "AAA111"),
        (no_disponible, "BBB222"),
        (no_aprobado, "CCC333"),
    ]:
        sembrar_vehiculo(sesion_bd, conductor.id, patente, AUTO)
    sembrar_vehiculo(sesion_bd, sin_el_tipo.id, "DDD444", MOTO)

    resultado = repositorio.listar(habilitado=True, disponible=True, tipo_vehiculo=AUTO)

    assert dnis(resultado) == ["30000001"]


def test_listar_con_filtros_sin_coincidencias_devuelve_lista_vacia(repositorio):
    repositorio.guardar(nuevo_conductor("30000001"))

    assert repositorio.listar(habilitado=True) == []
