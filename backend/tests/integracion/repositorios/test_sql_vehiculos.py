"""`SqlRepositorioVehiculos(session)`: el puerto `RepositorioVehiculos` sobre PostgreSQL.

Se comporta como el fake `RepositorioVehiculosEnMemoria` (ver `tests/unitarios/fakes`):
- `guardar` sin id inserta el vehiculo con sus tipos de servicio (cada uno con su
  `habilitado`) y devuelve el vehiculo de dominio con id asignado (1, 2, ...); el
  `id_conductor` lo setea el caso de uso antes de guardar y se conserva. Con id actualiza
  (habilitacion, `habilitado` de cada servicio) sin duplicar filas. Hace `flush`, no
  `commit`: los tests llaman a `sesion_bd.commit()`.
- `PatenteDuplicada` sale del `IntegrityError` de `uq_vehiculo_patente` (sin consulta
  previa); el INSERT, con sus tipos de servicio, se aisla en un SAVEPOINT para que la sesion
  siga usable y no queden filas hijas. Otro `IntegrityError` se propaga sin traducir.
- `obtener(id_conductor, id_vehiculo)` devuelve None si no existe o es de otro conductor.
- `listar_por_conductor` devuelve solo los del conductor, en orden de id, con `tipo` y
  `habilitacion` combinados con AND.
Los tipos de servicio vuelven en el orden del modelo ORM: los tests los comparan como
conjunto de pares (tipo, habilitado).
"""

import pytest
from app.dominio.errores import PatenteDuplicada
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.vehiculo import ServicioDelVehiculo, TipoServicio, TipoVehiculo, Vehiculo
from app.infraestructura.db.modelos import Conductor as ConductorOrm
from app.infraestructura.repositorios.sql_vehiculos import SqlRepositorioVehiculos
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError

PENDIENTE = EstadoHabilitacion.PENDIENTE
APROBADA = EstadoHabilitacion.APROBADA
AUTO = TipoVehiculo.AUTO
MOTO = TipoVehiculo.MOTO
PASAJEROS = TipoServicio.PASAJEROS
ENVIOS = TipoServicio.ENVIOS


@pytest.fixture
def repositorio(sesion_bd):
    return SqlRepositorioVehiculos(sesion_bd)


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


def nuevo_vehiculo(
    id_conductor,
    patente="AB123CD",
    tipo=AUTO,
    tipos_servicio=(PASAJEROS,),
    **estado,
):
    vehiculo = Vehiculo.crear(
        tipo=tipo,
        patente=patente,
        marca="Toyota",
        modelo="Etios",
        anio=2019,
        tipos_servicio=list(tipos_servicio),
    )
    vehiculo.id_conductor = id_conductor
    for atributo, valor in estado.items():
        setattr(vehiculo, atributo, valor)
    return vehiculo


def pares(vehiculo):
    return {(servicio.tipo, servicio.habilitado) for servicio in vehiculo.tipos_servicio}


def patentes(vehiculos):
    return [vehiculo.patente for vehiculo in vehiculos]


def contar_tipos_de_servicio(sesion):
    return sesion.execute(text("SELECT count(*) FROM vehiculo_tipo_servicio")).scalar_one()


# --- guardar y obtener ---


def test_guardar_vehiculo_nuevo_devuelve_el_vehiculo_de_dominio_con_ids_incrementales(
    repositorio, sesion_bd
):
    id_conductor = sembrar_conductor(sesion_bd)

    primero = repositorio.guardar(nuevo_vehiculo(id_conductor, "AAA111"))
    segundo = repositorio.guardar(nuevo_vehiculo(id_conductor, "BBB222"))

    assert isinstance(primero, Vehiculo)
    assert (primero.id, segundo.id) == (1, 2)
    assert primero.id_conductor == id_conductor
    assert primero.patente == "AAA111"


def test_guarda_los_tipos_de_servicio_con_su_habilitado(repositorio, sesion_bd, fabrica_sesiones):
    id_conductor = sembrar_conductor(sesion_bd)
    vehiculo = nuevo_vehiculo(id_conductor, tipos_servicio=(PASAJEROS, ENVIOS))
    vehiculo.tipos_servicio[0].habilitado = True  # PASAJEROS habilitado, ENVIOS no
    guardado = repositorio.guardar(vehiculo)
    sesion_bd.commit()

    assert contar_tipos_de_servicio(sesion_bd) == 2
    with fabrica_sesiones() as otra_sesion:
        leido = SqlRepositorioVehiculos(otra_sesion).obtener(id_conductor, guardado.id)
        assert pares(leido) == {(PASAJEROS, True), (ENVIOS, False)}


def test_el_vehiculo_confirmado_se_lee_con_todos_sus_campos_desde_otra_sesion(
    repositorio, sesion_bd, fabrica_sesiones
):
    id_conductor = sembrar_conductor(sesion_bd)
    vehiculo = nuevo_vehiculo(
        id_conductor,
        "AB123CD",
        MOTO,
        (PASAJEROS, ENVIOS),
        habilitacion=EstadoHabilitacion.OBSERVADA,
    )
    guardado = repositorio.guardar(vehiculo)
    sesion_bd.commit()

    with fabrica_sesiones() as otra_sesion:
        leido = SqlRepositorioVehiculos(otra_sesion).obtener(id_conductor, guardado.id)

    assert isinstance(leido, Vehiculo)
    assert leido.id == guardado.id
    assert leido.id_conductor == id_conductor
    assert leido.tipo is MOTO
    assert leido.patente == "AB123CD"
    assert leido.marca == "Toyota"
    assert leido.modelo == "Etios"
    assert leido.anio == 2019
    assert leido.habilitacion is EstadoHabilitacion.OBSERVADA
    assert all(isinstance(s, ServicioDelVehiculo) for s in leido.tipos_servicio)
    assert pares(leido) == {(PASAJEROS, False), (ENVIOS, False)}


def test_obtener_vehiculo_inexistente_devuelve_none(repositorio, sesion_bd):
    id_conductor = sembrar_conductor(sesion_bd)
    guardado = repositorio.guardar(nuevo_vehiculo(id_conductor))

    assert repositorio.obtener(id_conductor, guardado.id + 1) is None


def test_obtener_vehiculo_de_otro_conductor_devuelve_none(repositorio, sesion_bd):
    duenio = sembrar_conductor(sesion_bd, "30000001")
    otro = sembrar_conductor(sesion_bd, "30000002")
    guardado = repositorio.guardar(nuevo_vehiculo(duenio))

    assert repositorio.obtener(otro, guardado.id) is None


def test_guardar_un_vehiculo_con_id_lo_actualiza_sin_duplicar_filas(
    repositorio, sesion_bd, fabrica_sesiones
):
    id_conductor = sembrar_conductor(sesion_bd)
    vehiculo = repositorio.guardar(nuevo_vehiculo(id_conductor, tipos_servicio=(PASAJEROS, ENVIOS)))
    sesion_bd.commit()
    vehiculo.habilitacion = APROBADA
    vehiculo.tipos_servicio[0].habilitado = True

    actualizado = repositorio.guardar(vehiculo)
    sesion_bd.commit()

    assert actualizado.id == vehiculo.id
    assert contar_tipos_de_servicio(sesion_bd) == 2
    with fabrica_sesiones() as otra_sesion:
        repositorio_otra = SqlRepositorioVehiculos(otra_sesion)
        leido = repositorio_otra.obtener(id_conductor, vehiculo.id)
        assert leido.habilitacion is APROBADA
        assert {(s.tipo, s.habilitado) for s in vehiculo.tipos_servicio} == pares(leido)
        assert sum(habilitado for _, habilitado in pares(leido)) == 1
        assert len(repositorio_otra.listar_por_conductor(id_conductor)) == 1


# --- PatenteDuplicada ---


@pytest.mark.parametrize(
    "mismo_conductor", [True, False], ids=["mismo_conductor", "otro_conductor"]
)
def test_guardar_con_patente_existente_lanza_patente_duplicada(
    repositorio, sesion_bd, mismo_conductor
):
    duenio = sembrar_conductor(sesion_bd, "30000001")
    otro = sembrar_conductor(sesion_bd, "30000002")
    repositorio.guardar(nuevo_vehiculo(duenio, "AAA111"))

    with pytest.raises(PatenteDuplicada):
        repositorio.guardar(nuevo_vehiculo(duenio if mismo_conductor else otro, "AAA111"))


def test_la_sesion_sigue_usable_y_no_quedan_filas_hijas_tras_una_patente_duplicada(
    repositorio, sesion_bd, fabrica_sesiones
):
    duenio = sembrar_conductor(sesion_bd, "30000001")
    otro = sembrar_conductor(sesion_bd, "30000002")
    original = repositorio.guardar(nuevo_vehiculo(duenio, "AAA111", tipos_servicio=(PASAJEROS,)))

    with pytest.raises(PatenteDuplicada):
        repositorio.guardar(nuevo_vehiculo(otro, "AAA111", tipos_servicio=(PASAJEROS, ENVIOS)))

    assert repositorio.obtener(duenio, original.id).patente == "AAA111"  # sin rollback manual
    assert contar_tipos_de_servicio(sesion_bd) == 1
    sesion_bd.commit()
    with fabrica_sesiones() as otra_sesion:
        repositorio_otra = SqlRepositorioVehiculos(otra_sesion)
        assert patentes(repositorio_otra.listar_por_conductor(duenio)) == ["AAA111"]
        assert repositorio_otra.listar_por_conductor(otro) == []


def test_la_patente_duplicada_se_detecta_con_el_insert_y_no_con_una_consulta_previa(
    repositorio, sesion_bd
):
    id_conductor = sembrar_conductor(sesion_bd)
    repositorio.guardar(nuevo_vehiculo(id_conductor, "AAA111"))
    sentencias = []

    def registrar(conexion, cursor, sentencia, parametros, contexto, ejecutar_muchos):
        sentencias.append(sentencia.lstrip().upper())

    motor = sesion_bd.get_bind()
    event.listen(motor, "before_cursor_execute", registrar)
    try:
        with pytest.raises(PatenteDuplicada):
            repositorio.guardar(nuevo_vehiculo(id_conductor, "AAA111"))
    finally:
        event.remove(motor, "before_cursor_execute", registrar)

    assert any(sentencia.startswith("INSERT") for sentencia in sentencias)
    assert not any(sentencia.startswith("SELECT") for sentencia in sentencias)


def test_un_integrity_error_que_no_es_de_patente_no_se_traduce_a_patente_duplicada(
    repositorio, sesion_bd
):
    id_conductor = sembrar_conductor(sesion_bd)
    anio_fuera_de_rango = nuevo_vehiculo(id_conductor)
    anio_fuera_de_rango.anio = 1800  # viola ck_vehiculo_anio_valido

    with pytest.raises(IntegrityError):
        repositorio.guardar(anio_fuera_de_rango)


# --- listar_por_conductor ---


def test_listar_de_un_conductor_sin_vehiculos_o_inexistente_devuelve_lista_vacia(
    repositorio, sesion_bd
):
    id_conductor = sembrar_conductor(sesion_bd)

    assert repositorio.listar_por_conductor(id_conductor) == []
    assert repositorio.listar_por_conductor(id_conductor + 1) == []


def test_listar_devuelve_solo_los_del_conductor_en_orden_de_id_con_sus_servicios(
    repositorio, sesion_bd
):
    uno = sembrar_conductor(sesion_bd, "30000001")
    otro = sembrar_conductor(sesion_bd, "30000002")
    repositorio.guardar(nuevo_vehiculo(uno, "CCC333", tipos_servicio=(PASAJEROS, ENVIOS)))
    repositorio.guardar(nuevo_vehiculo(otro, "ZZZ999"))
    repositorio.guardar(nuevo_vehiculo(uno, "AAA111", tipos_servicio=(ENVIOS,)))

    resultado = repositorio.listar_por_conductor(uno)

    assert patentes(resultado) == ["CCC333", "AAA111"]
    assert [v.id for v in resultado] == [1, 3]
    assert all(isinstance(v, Vehiculo) for v in resultado)
    assert [pares(v) for v in resultado] == [
        {(PASAJEROS, False), (ENVIOS, False)},
        {(ENVIOS, False)},
    ]


@pytest.mark.parametrize(
    ("filtros", "patentes_esperadas"),
    [
        ({"tipo": AUTO}, ["AUTO-PEND", "AUTO-APROB"]),
        ({"tipo": MOTO}, ["MOTO-PEND", "MOTO-APROB"]),
        ({"habilitacion": APROBADA}, ["AUTO-APROB", "MOTO-APROB"]),
        ({"habilitacion": PENDIENTE}, ["AUTO-PEND", "MOTO-PEND"]),
        ({"tipo": MOTO, "habilitacion": APROBADA}, ["MOTO-APROB"]),
        ({"tipo": AUTO, "habilitacion": PENDIENTE}, ["AUTO-PEND"]),
    ],
    ids=[
        "por_tipo_auto",
        "por_tipo_moto",
        "por_habilitacion_aprobada",
        "por_habilitacion_pendiente",
        "moto_y_aprobada",
        "auto_y_pendiente",
    ],
)
def test_listar_filtra_por_tipo_y_habilitacion_combinando_con_and(
    repositorio, sesion_bd, filtros, patentes_esperadas
):
    id_conductor = sembrar_conductor(sesion_bd)
    otro = sembrar_conductor(sesion_bd, "30000002")
    repositorio.guardar(nuevo_vehiculo(id_conductor, "AUTO-PEND", AUTO, habilitacion=PENDIENTE))
    repositorio.guardar(nuevo_vehiculo(id_conductor, "AUTO-APROB", AUTO, habilitacion=APROBADA))
    repositorio.guardar(nuevo_vehiculo(id_conductor, "MOTO-PEND", MOTO, habilitacion=PENDIENTE))
    repositorio.guardar(nuevo_vehiculo(id_conductor, "MOTO-APROB", MOTO, habilitacion=APROBADA))
    repositorio.guardar(nuevo_vehiculo(otro, "AJENO", MOTO, habilitacion=APROBADA))

    resultado = repositorio.listar_por_conductor(id_conductor, **filtros)

    assert patentes(resultado) == patentes_esperadas


def test_listar_con_filtros_sin_coincidencias_devuelve_lista_vacia(repositorio, sesion_bd):
    id_conductor = sembrar_conductor(sesion_bd)
    repositorio.guardar(nuevo_vehiculo(id_conductor, "AAA111", AUTO))

    assert repositorio.listar_por_conductor(id_conductor, habilitacion=APROBADA) == []
