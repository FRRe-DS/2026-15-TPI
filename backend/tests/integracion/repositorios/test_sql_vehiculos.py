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
Los dos ultimos tests de la seccion "caracterizacion" (quitar un tipo de servicio al
actualizar y guardar con un id inexistente) son de CARACTERIZACION: fijan decisiones tomadas
en la implementacion y pasan de entrada, sin fase Red.
"""

import pytest
from app.dominio.errores import NoEncontrado, PatenteDuplicada
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.vehiculo import ServicioDelVehiculo, TipoServicio, TipoVehiculo, Vehiculo
from app.infraestructura.db.modelos import Conductor as ConductorOrm
from app.infraestructura.repositorios.sql_vehiculos import SqlRepositorioVehiculos
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError

from tests.integracion.sentencias import capturar_sentencias, selects

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


# --- listar_por_conductores (lote) ---


def sembrar_flota(repositorio, sesion, conductores, vehiculos_por_conductor):
    """Siembra y confirma conductores con vehiculos de 2 tipos de servicio; devuelve sus ids."""
    ids = []
    numero_de_patente = 0
    for n in range(1, conductores + 1):
        id_conductor = sembrar_conductor(sesion, f"3000{n:04d}")
        ids.append(id_conductor)
        for _ in range(vehiculos_por_conductor):
            numero_de_patente += 1
            repositorio.guardar(
                nuevo_vehiculo(
                    id_conductor, f"PAT{numero_de_patente:03d}", tipos_servicio=(PASAJEROS, ENVIOS)
                )
            )
    sesion.commit()
    return ids


def test_listar_por_conductores_devuelve_una_clave_por_id_pedido_con_sus_vehiculos_y_servicios(
    repositorio, sesion_bd, fabrica_sesiones
):
    con_vehiculos = sembrar_conductor(sesion_bd, "30000001")
    sin_vehiculos = sembrar_conductor(sesion_bd, "30000002")
    vehiculo = nuevo_vehiculo(con_vehiculos, "AAA111", MOTO, (PASAJEROS, ENVIOS))
    vehiculo.tipos_servicio[1].habilitado = True  # ENVIOS habilitado, PASAJEROS no
    repositorio.guardar(vehiculo)
    sesion_bd.commit()

    with fabrica_sesiones() as otra_sesion:
        resultado = SqlRepositorioVehiculos(otra_sesion).listar_por_conductores(
            [con_vehiculos, sin_vehiculos]
        )

    assert set(resultado) == {con_vehiculos, sin_vehiculos}
    assert resultado[sin_vehiculos] == []
    [leido] = resultado[con_vehiculos]
    assert isinstance(leido, Vehiculo)
    assert (leido.patente, leido.tipo, leido.id_conductor) == ("AAA111", MOTO, con_vehiculos)
    assert all(isinstance(s, ServicioDelVehiculo) for s in leido.tipos_servicio)
    assert pares(leido) == {(PASAJEROS, False), (ENVIOS, True)}


def test_listar_por_conductores_devuelve_cada_lista_en_orden_de_alta(
    repositorio, sesion_bd, fabrica_sesiones
):
    uno = sembrar_conductor(sesion_bd, "30000001")
    otro = sembrar_conductor(sesion_bd, "30000002")
    altas = [(uno, "CCC333"), (otro, "XXX111"), (uno, "AAA111"), (otro, "YYY222")]
    for id_conductor, patente in altas:
        repositorio.guardar(nuevo_vehiculo(id_conductor, patente))
    sesion_bd.commit()

    with fabrica_sesiones() as otra_sesion:
        resultado = SqlRepositorioVehiculos(otra_sesion).listar_por_conductores([otro, uno])

    assert patentes(resultado[uno]) == ["CCC333", "AAA111"]
    assert patentes(resultado[otro]) == ["XXX111", "YYY222"]


def test_listar_por_conductores_no_mezcla_los_ids_no_pedidos(repositorio, sesion_bd):
    pedido = sembrar_conductor(sesion_bd, "30000001")
    no_pedido = sembrar_conductor(sesion_bd, "30000002")
    repositorio.guardar(nuevo_vehiculo(pedido, "PEDIDO1"))
    repositorio.guardar(nuevo_vehiculo(no_pedido, "AJENO11"))

    resultado = repositorio.listar_por_conductores([pedido])

    assert set(resultado) == {pedido}
    assert patentes(resultado[pedido]) == ["PEDIDO1"]


def test_listar_por_conductores_sin_ids_devuelve_un_diccionario_vacio(repositorio, sesion_bd):
    sembrar_flota(repositorio, sesion_bd, conductores=1, vehiculos_por_conductor=1)

    assert repositorio.listar_por_conductores([]) == {}


def test_listar_por_conductores_con_ids_inexistentes_devuelve_listas_vacias(repositorio):
    assert repositorio.listar_por_conductores([998, 999]) == {998: [], 999: []}


def test_el_lote_de_vehiculos_hace_una_cantidad_de_selects_que_no_crece_con_los_conductores(
    repositorio, sesion_bd, fabrica_sesiones, engine_integracion
):
    ids = sembrar_flota(repositorio, sesion_bd, conductores=6, vehiculos_por_conductor=3)

    def selects_para(ids_pedidos):
        with fabrica_sesiones() as sesion_nueva:  # sesion sin objetos en cache
            with capturar_sentencias(engine_integracion) as sentencias:
                SqlRepositorioVehiculos(sesion_nueva).listar_por_conductores(ids_pedidos)
        return len(selects(sentencias))

    con_2_conductores = selects_para(ids[:2])
    con_6_conductores = selects_para(ids)

    assert con_2_conductores == con_6_conductores
    assert con_6_conductores <= 2


def test_listar_por_conductor_hace_una_cantidad_constante_de_selects_sin_n_mas_1(
    repositorio, sesion_bd, fabrica_sesiones, engine_integracion
):
    con_un_vehiculo = sembrar_conductor(sesion_bd, "30000001")
    con_cinco_vehiculos = sembrar_conductor(sesion_bd, "30000002")
    repositorio.guardar(
        nuevo_vehiculo(con_un_vehiculo, "UNO0001", tipos_servicio=(PASAJEROS, ENVIOS))
    )
    for n in range(5):
        repositorio.guardar(
            nuevo_vehiculo(con_cinco_vehiculos, f"CIN000{n}", tipos_servicio=(PASAJEROS, ENVIOS))
        )
    sesion_bd.commit()

    def selects_para(id_conductor):
        with fabrica_sesiones() as sesion_nueva:  # sesion sin objetos en cache
            with capturar_sentencias(engine_integracion) as sentencias:
                resultado = SqlRepositorioVehiculos(sesion_nueva).listar_por_conductor(id_conductor)
                assert all(len(v.tipos_servicio) == 2 for v in resultado)
        return len(selects(sentencias))

    con_uno = selects_para(con_un_vehiculo)
    con_cinco = selects_para(con_cinco_vehiculos)

    assert con_uno == con_cinco
    assert con_cinco <= 2


# --- Caracterizacion: decisiones de la implementacion fijadas despues de escribirla ---


def test_guardar_un_vehiculo_que_paso_de_dos_tipos_de_servicio_a_uno_quita_la_fila_sobrante(
    repositorio, sesion_bd, fabrica_sesiones
):
    """Caracterizacion: el comportamiento ya existia cuando se escribio este test."""
    id_conductor = sembrar_conductor(sesion_bd)
    vehiculo = nuevo_vehiculo(id_conductor, tipos_servicio=(PASAJEROS, ENVIOS))
    vehiculo.tipos_servicio[1].habilitado = True  # ENVIOS habilitado, PASAJEROS no
    repositorio.guardar(vehiculo)
    sesion_bd.commit()
    vehiculo.tipos_servicio = [s for s in vehiculo.tipos_servicio if s.tipo is ENVIOS]

    repositorio.guardar(vehiculo)
    sesion_bd.commit()

    with fabrica_sesiones() as otra_sesion:
        assert contar_tipos_de_servicio(otra_sesion) == 1
        leido = SqlRepositorioVehiculos(otra_sesion).obtener(id_conductor, vehiculo.id)
        assert pares(leido) == {(ENVIOS, True)}


def test_guardar_un_vehiculo_con_id_inexistente_lanza_no_encontrado_y_no_deja_filas(
    repositorio, sesion_bd
):
    """Caracterizacion: los ids los genera la base; un id inexistente no es un alta."""
    id_conductor = sembrar_conductor(sesion_bd)
    vehiculo = nuevo_vehiculo(id_conductor)
    vehiculo.id = 999

    with pytest.raises(NoEncontrado):
        repositorio.guardar(vehiculo)

    assert repositorio.listar_por_conductor(id_conductor) == []
    assert contar_tipos_de_servicio(sesion_bd) == 0
