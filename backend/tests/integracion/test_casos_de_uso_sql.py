"""Equivalencia entre los fakes y la base real para los casos de uso de la Iteracion 1.

`ejecutar_escenario(uow, reloj)` corre una secuencia con los casos de uso REALES de
`app.aplicacion.casos_de_uso` (cada uno con su propio `with`) y devuelve los resultados
normalizados: solo valores (estados, listas, errores capturados por nombre), nunca objetos.
Los ids se reemplazan por alias ("A", "AAA111", ...) porque las secuencias de PostgreSQL
dejan huecos cuando un INSERT falla (DniDuplicado, PatenteDuplicada) y el fake no.

- El test de equivalencia corre el MISMO escenario con `UnidadDeTrabajoEnMemoria` y con
  `SqlUnidadDeTrabajo` y exige resultados identicos paso a paso.
- Otro test, parametrizado por backend, compara pasos clave contra el valor esperado segun
  la especificacion (detecta un bug comun a los dos).
- Los tests solo-SQL miran la base desde una sesion nueva (persistencia, rollback, FOR UPDATE).

Son tests de integracion de codigo que ya existe: se espera que la mayoria pase de entrada.
El valor esta en detectar diferencias entre fake y SQL; si una aparece, se reporta, no se
ajusta el test.
"""

from datetime import UTC, date, datetime

import pytest
from app.aplicacion.casos_de_uso.accionar_habilitacion_conductor import (
    AccionarHabilitacionConductor,
)
from app.aplicacion.casos_de_uso.accionar_habilitacion_vehiculo import (
    AccionarHabilitacionVehiculo,
)
from app.aplicacion.casos_de_uso.consultar_habilitacion_conductor import (
    ConsultarHabilitacionConductor,
)
from app.aplicacion.casos_de_uso.crear_conductor import CrearConductor
from app.aplicacion.casos_de_uso.listar_conductores import ListarConductores
from app.aplicacion.casos_de_uso.listar_vehiculos import ListarVehiculos
from app.aplicacion.casos_de_uso.obtener_conductor import ObtenerConductor
from app.aplicacion.casos_de_uso.obtener_vehiculo import ObtenerVehiculo
from app.aplicacion.casos_de_uso.registrar_licencia import RegistrarLicencia
from app.aplicacion.casos_de_uso.registrar_vehiculo import RegistrarVehiculo
from app.dominio.errores import (
    DatosInvalidos,
    DniDuplicado,
    LicenciaVigenteRequerida,
    PatenteDuplicada,
)
from app.dominio.habilitacion import AccionHabilitacion, EstadoHabilitacion
from app.dominio.vehiculo import TipoServicio, TipoVehiculo
from app.infraestructura.repositorios.sql_unidad_de_trabajo import SqlUnidadDeTrabajo
from sqlalchemy import text

from tests.integracion.sentencias import capturar_sentencias
from tests.unitarios.fakes.reloj_fijo import RelojFijo
from tests.unitarios.fakes.repositorios_en_memoria import UnidadDeTrabajoEnMemoria

AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
URL = "https://almacen.example.com/licencias/lic.pdf"
ID_OPERADOR = 7

APROBAR = AccionHabilitacion.APROBAR
OBSERVAR = AccionHabilitacion.OBSERVAR
SUSPENDER = AccionHabilitacion.SUSPENDER
RECHAZAR = AccionHabilitacion.RECHAZAR
ALTA = AccionHabilitacion.ALTA
AUTO = TipoVehiculo.AUTO
MOTO = TipoVehiculo.MOTO
PASAJEROS = TipoServicio.PASAJEROS
ENVIOS = TipoServicio.ENVIOS


# --- Normalizacion: de objetos de dominio a valores comparables ---


class Normalizador:
    def __init__(self):
        self._alias = {}

    def registrar(self, tipo, id_real, nombre):
        self._alias[(tipo, id_real)] = nombre

    def id(self, tipo, id_real):
        return self._alias.get((tipo, id_real), f"?{tipo}:{id_real}")

    def conductor(self, c):
        return {
            "id": self.id("conductor", c.id),
            "dni": c.dni,
            "nombre": c.nombre,
            "apellido": c.apellido,
            "telefono": c.telefono,
            "email": c.email,
            "habilitacion": c.habilitacion.value,
            "conectado": c.conectado,
            "disponible": c.disponible,
        }

    def documento(self, d):
        return {
            "id": self.id("documento", d.id),
            "tipo": d.tipo.value,
            "numero": d.numero,
            "categoria": d.categoria,
            "emision": d.fecha_emision.isoformat(),
            "vencimiento": d.fecha_vencimiento.isoformat(),
            "url": d.url_archivo,
        }

    def vehiculo(self, v):
        return {
            "id": self.id("vehiculo", v.id),
            "conductor": self.id("conductor", v.id_conductor),
            "tipo": v.tipo.value,
            "patente": v.patente,
            "marca": v.marca,
            "modelo": v.modelo,
            "anio": v.anio,
            "habilitacion": v.habilitacion.value,
            "servicios": sorted((s.tipo.value, s.habilitado) for s in v.tipos_servicio),
        }

    def detalle_de_conductor(self, d):
        return {
            "conductor": self.conductor(d.conductor),
            "documentos": [
                {**self.documento(x.documento), "estado": x.estado.value} for x in d.documentos
            ],
            "vehiculos": [self.vehiculo(v) for v in d.vehiculos],
        }

    def detalle_de_vehiculo(self, d):
        return {"vehiculo": self.vehiculo(d.vehiculo), "documentos": list(d.documentos)}


def evento(e):
    return {
        "accion": e.accion.value,
        "anterior": None if e.estado_anterior is None else e.estado_anterior.value,
        "nuevo": e.estado_nuevo.value,
        "motivo": e.motivo,
        "operador": e.id_operador,
        "fecha": e.fecha.astimezone(UTC).isoformat(),
    }


# --- Escenario ---


def ejecutar_escenario(uow, reloj):
    n = Normalizador()
    r = {}
    id_de = {}  # alias -> id real (conductores y vehiculos)

    crear = CrearConductor(uow, reloj)
    registrar_licencia = RegistrarLicencia(uow, reloj)
    accionar_conductor = AccionarHabilitacionConductor(uow, reloj)
    consultar_habilitacion = ConsultarHabilitacionConductor(uow)
    obtener_conductor = ObtenerConductor(uow, reloj)
    listar_conductores = ListarConductores(uow, reloj)
    registrar_vehiculo = RegistrarVehiculo(uow, reloj)
    listar_vehiculos = ListarVehiculos(uow)
    obtener_vehiculo = ObtenerVehiculo(uow)
    accionar_vehiculo = AccionarHabilitacionVehiculo(uow, reloj)

    def intentar(clave, funcion):
        try:
            r[clave] = {"ok": funcion()}
        except Exception as error:
            r[clave] = {"error": type(error).__name__}

    def datos_de(alias, dni):
        return {
            "dni": dni,
            "nombre": alias,
            "apellido": "Perez",
            "telefono": "+54 379 4000000",
            "email": f"{alias.lower()}@example.com",
        }

    # -- Conductores
    for alias, dni in (("A", "30000001"), ("B", "30000002"), ("C", "30000003")):
        detalle = crear.ejecutar(**datos_de(alias, dni))
        id_de[alias] = detalle.conductor.id
        n.registrar("conductor", detalle.conductor.id, alias)
        r[f"crear_{alias}"] = n.detalle_de_conductor(detalle)

    intentar("crear_dni_duplicado", lambda: crear.ejecutar(**datos_de("Otro", "30000001")))
    r["dnis_tras_dni_duplicado"] = [d.conductor.dni for d in listar_conductores.ejecutar()]
    r["historiales_tras_dni_duplicado"] = {
        alias: [evento(e) for e in consultar_habilitacion.ejecutar(id_conductor=i).historial]
        for alias, i in id_de.items()
    }

    # -- Licencias
    hoy = reloj.hoy()

    def licencia(clave, id_conductor, numero, vencimiento):
        try:
            res = registrar_licencia.ejecutar(
                id_conductor=id_conductor,
                numero=numero,
                categoria="B1",
                fecha_emision=date(2020, 1, 1),
                fecha_vencimiento=vencimiento,
                url_archivo=URL,
            )
        except Exception as error:
            r[clave] = {"error": type(error).__name__}
            return
        n.registrar("documento", res.documento.id, numero)
        r[clave] = {
            "ok": {
                "conductor": n.id("conductor", res.id_conductor),
                "documento": n.documento(res.documento),
                "estado": res.estado.value,
            }
        }

    licencia("licencia_B_vence_hoy", id_de["B"], "L-HOY", hoy)
    licencia("licencia_A_vencida", id_de["A"], "L-VENCIDA", date(2026, 6, 14))
    licencia("licencia_A_futura", id_de["A"], "L-FUTURA", date(2029, 1, 1))
    licencia("licencia_conductor_inexistente", 999, "L-X", date(2029, 1, 1))
    licencia("licencia_fechas_invalidas", id_de["C"], "L-Y", date(2020, 1, 1))

    # -- Habilitacion del conductor
    def accion_conductor(clave, alias, accion, motivo="Revision", id_operador=ID_OPERADOR):
        id_conductor = id_de.get(alias, 999)
        intentar(
            clave,
            lambda: _eventos_de_conductor(
                n,
                accionar_conductor.ejecutar(
                    id_conductor=id_conductor,
                    accion=accion,
                    motivo=motivo,
                    id_operador=id_operador,
                ),
            ),
        )

    def estado_de_habilitacion(clave, alias):
        id_conductor = id_de.get(alias, 999)
        intentar(
            clave,
            lambda: _resumen(n, consultar_habilitacion.ejecutar(id_conductor=id_conductor)),
        )

    accion_conductor("C_aprobar_sin_licencia", "C", APROBAR)
    estado_de_habilitacion("C_estado_tras_aprobar_sin_licencia", "C")
    accion_conductor("C_observar_sin_licencia", "C", OBSERVAR)
    accion_conductor("B_aprobar_con_licencia_que_vence_hoy", "B", APROBAR, "Licencia vigente")
    reloj.avanzar(dias=1)
    accion_conductor("A_aprobar_con_licencia_futura_y_una_vencida", "A", APROBAR, "Todo en orden")
    reloj.avanzar(dias=1)
    accion_conductor("A_suspender", "A", SUSPENDER, "Revision de documentos")
    reloj.avanzar(dias=1)
    accion_conductor("A_volver_a_aprobar", "A", APROBAR, "Documentos regularizados")
    accion_conductor("A_aprobar_estando_aprobada", "A", APROBAR)
    accion_conductor("A_suspender_con_motivo_en_blanco", "A", SUSPENDER, "   ")
    accion_conductor("A_alta_manual", "A", ALTA)
    accion_conductor("C_rechazar", "C", RECHAZAR, "No cumple requisitos")
    accion_conductor("C_observar_estando_rechazada", "C", OBSERVAR)
    accion_conductor("conductor_inexistente_accion", "inexistente", OBSERVAR)
    for alias in ("A", "B", "C"):
        estado_de_habilitacion(f"historial_{alias}", alias)
    estado_de_habilitacion("historial_inexistente", "inexistente")

    # -- Vehiculos
    def vehiculo(clave, alias, tipo, patente, servicios, anio=2019):
        id_conductor = id_de.get(alias, 999)

        def registrar():
            detalle = registrar_vehiculo.ejecutar(
                id_conductor=id_conductor,
                tipo=tipo,
                patente=patente,
                marca="Toyota",
                modelo="Etios",
                anio=anio,
                tipos_servicio=servicios,
            )
            id_de[patente] = detalle.vehiculo.id
            n.registrar("vehiculo", detalle.vehiculo.id, patente)
            return n.detalle_de_vehiculo(detalle)

        intentar(clave, registrar)

    vehiculo("vehiculo_A_auto", "A", AUTO, "AAA111", [PASAJEROS, ENVIOS])
    vehiculo("vehiculo_A_moto", "A", MOTO, "BBB222", [ENVIOS])
    vehiculo("vehiculo_B_auto", "B", AUTO, "CCC333", [PASAJEROS])
    vehiculo("vehiculo_C_moto", "C", MOTO, "DDD444", [PASAJEROS])
    vehiculo("patente_duplicada_de_otro_conductor", "B", AUTO, "AAA111", [PASAJEROS])
    vehiculo("patente_duplicada_del_mismo_conductor", "A", MOTO, "BBB222", [ENVIOS])
    vehiculo("vehiculo_de_conductor_inexistente", "inexistente", AUTO, "EEE555", [PASAJEROS])
    vehiculo("vehiculo_con_anio_no_entero", "A", AUTO, "FFF666", [PASAJEROS], anio="2019")
    vehiculo("vehiculo_sin_servicios", "A", AUTO, "GGG777", [])
    vehiculo("vehiculo_con_servicios_repetidos", "A", AUTO, "HHH888", [ENVIOS, ENVIOS])

    def accion_vehiculo(clave, alias_conductor, patente, accion, motivo="Revision"):
        id_conductor = id_de.get(alias_conductor, 999)
        id_vehiculo = id_de.get(patente, 999)
        intentar(
            clave,
            lambda: _eventos_de_vehiculo(
                n,
                accionar_vehiculo.ejecutar(
                    id_conductor=id_conductor,
                    id_vehiculo=id_vehiculo,
                    accion=accion,
                    motivo=motivo,
                    id_operador=ID_OPERADOR,
                ),
            ),
        )

    reloj.avanzar(dias=1)
    accion_vehiculo("C_vehiculo_aprobar_sin_licencia", "C", "DDD444", APROBAR, "Cedula verificada")
    accion_vehiculo("C_vehiculo_observar_estando_aprobado", "C", "DDD444", OBSERVAR)
    reloj.avanzar(dias=1)
    accion_vehiculo("C_vehiculo_suspender", "C", "DDD444", SUSPENDER, "Siniestro")
    reloj.avanzar(dias=1)
    accion_vehiculo("C_vehiculo_rechazar", "C", "DDD444", RECHAZAR, "Baja definitiva")
    accion_vehiculo("C_vehiculo_aprobar_estando_rechazado", "C", "DDD444", APROBAR)
    accion_vehiculo("A_vehiculo_aprobar", "A", "AAA111", APROBAR, "Todo en orden")
    accion_vehiculo("A_vehiculo_observar_con_motivo_vacio", "A", "BBB222", OBSERVAR, "")
    accion_vehiculo("A_vehiculo_alta_manual", "A", "BBB222", ALTA)
    accion_vehiculo("vehiculo_de_otro_conductor_accion", "B", "AAA111", OBSERVAR)
    accion_vehiculo("vehiculo_inexistente_accion", "A", "inexistente", OBSERVAR)

    def listar_veh(clave, alias, **filtros):
        id_conductor = id_de.get(alias, 999)
        intentar(
            clave,
            lambda: [
                n.vehiculo(v)
                for v in listar_vehiculos.ejecutar(id_conductor=id_conductor, **filtros)
            ],
        )

    listar_veh("vehiculos_de_A", "A")
    listar_veh("vehiculos_de_A_motos", "A", tipo=MOTO)
    listar_veh("vehiculos_de_A_aprobados", "A", habilitacion=EstadoHabilitacion.APROBADA)
    listar_veh(
        "vehiculos_de_A_motos_aprobadas", "A", tipo=MOTO, habilitacion=EstadoHabilitacion.APROBADA
    )
    listar_veh("vehiculos_de_C_rechazados", "C", habilitacion=EstadoHabilitacion.RECHAZADA)
    listar_veh("vehiculos_de_inexistente", "inexistente")

    def obtener_veh(clave, alias_conductor, patente):
        id_conductor = id_de.get(alias_conductor, 999)
        id_vehiculo = id_de.get(patente, 999)
        intentar(
            clave,
            lambda: n.detalle_de_vehiculo(
                obtener_vehiculo.ejecutar(id_conductor=id_conductor, id_vehiculo=id_vehiculo)
            ),
        )

    obtener_veh("obtener_vehiculo_A_AAA111", "A", "AAA111")
    obtener_veh("obtener_vehiculo_de_otro_conductor", "B", "AAA111")
    obtener_veh("obtener_vehiculo_inexistente", "A", "inexistente")
    obtener_veh("obtener_vehiculo_con_conductor_inexistente", "inexistente", "AAA111")

    # -- Lecturas de conductores
    for alias in ("A", "B", "C"):
        intentar(
            f"obtener_{alias}",
            lambda alias=alias: n.detalle_de_conductor(
                obtener_conductor.ejecutar(id_conductor=id_de[alias])
            ),
        )
    intentar("obtener_inexistente", lambda: obtener_conductor.ejecutar(id_conductor=999))

    with uow:  # el unico modo de marcar "disponible" en la Iteracion 1 es guardar directo
        conductor_b = uow.conductores.obtener(id_de["B"])
        conductor_b.disponible = True
        uow.conductores.guardar(conductor_b)
        uow.commit()

    def listar_cond(clave, **filtros):
        intentar(
            clave,
            lambda: [n.detalle_de_conductor(d) for d in listar_conductores.ejecutar(**filtros)],
        )

    listar_cond("listar_todos")
    listar_cond("listar_habilitados", habilitado=True)
    listar_cond("listar_no_habilitados", habilitado=False)
    listar_cond("listar_disponibles", disponible=True)
    listar_cond("listar_no_disponibles", disponible=False)
    listar_cond("listar_con_auto", tipo_vehiculo=AUTO)
    listar_cond("listar_con_moto", tipo_vehiculo=MOTO)
    listar_cond("listar_habilitados_con_moto", habilitado=True, tipo_vehiculo=MOTO)
    listar_cond(
        "listar_habilitados_disponibles_con_auto",
        habilitado=True,
        disponible=True,
        tipo_vehiculo=AUTO,
    )
    listar_cond("listar_sin_coincidencias", habilitado=False, disponible=True)
    return r


def _eventos_de_conductor(n, resultado):
    return {
        "conductor": n.id("conductor", resultado.id_conductor),
        "estado": resultado.estado.value,
        "eventos": [evento(e) for e in resultado.eventos],
    }


def _resumen(n, resultado):
    return {
        "conductor": n.id("conductor", resultado.id_conductor),
        "estado": resultado.estado.value,
        "historial": [evento(e) for e in resultado.historial],
    }


def _eventos_de_vehiculo(n, resultado):
    return {
        "vehiculo": n.id("vehiculo", resultado.id_vehiculo),
        "estado": resultado.estado.value,
        "eventos": [evento(e) for e in resultado.eventos],
    }


# --- Tests de equivalencia ---


@pytest.fixture
def uow_sql(fabrica_sesiones, sesion_bd):
    """Depende de `sesion_bd` para que la base se limpie al terminar cada prueba."""
    return SqlUnidadDeTrabajo(fabrica_sesiones)


def test_el_escenario_completo_da_los_mismos_resultados_con_el_fake_y_con_sql(uow_sql):
    con_fake = ejecutar_escenario(UnidadDeTrabajoEnMemoria(), RelojFijo(AHORA))
    con_sql = ejecutar_escenario(uow_sql, RelojFijo(AHORA))

    assert list(con_fake) == list(con_sql)
    diferencias = {
        paso: {"fake": con_fake[paso], "sql": con_sql[paso]}
        for paso in con_fake
        if con_fake[paso] != con_sql[paso]
    }
    assert diferencias == {}


ERRORES_ESPERADOS = {
    "crear_dni_duplicado": "DniDuplicado",
    "licencia_conductor_inexistente": "NoEncontrado",
    "licencia_fechas_invalidas": "DatosInvalidos",
    "C_aprobar_sin_licencia": "LicenciaVigenteRequerida",
    "A_aprobar_estando_aprobada": "TransicionInvalida",
    "A_suspender_con_motivo_en_blanco": "DatosInvalidos",
    "A_alta_manual": "TransicionInvalida",
    "C_observar_estando_rechazada": "TransicionInvalida",
    "conductor_inexistente_accion": "NoEncontrado",
    "historial_inexistente": "NoEncontrado",
    "patente_duplicada_de_otro_conductor": "PatenteDuplicada",
    "patente_duplicada_del_mismo_conductor": "PatenteDuplicada",
    "vehiculo_de_conductor_inexistente": "NoEncontrado",
    "vehiculo_con_anio_no_entero": "DatosInvalidos",
    "vehiculo_sin_servicios": "DatosInvalidos",
    "vehiculo_con_servicios_repetidos": "DatosInvalidos",
    "C_vehiculo_observar_estando_aprobado": "TransicionInvalida",
    "C_vehiculo_aprobar_estando_rechazado": "TransicionInvalida",
    "A_vehiculo_observar_con_motivo_vacio": "DatosInvalidos",
    "A_vehiculo_alta_manual": "TransicionInvalida",
    "vehiculo_de_otro_conductor_accion": "NoEncontrado",
    "vehiculo_inexistente_accion": "NoEncontrado",
    "vehiculos_de_inexistente": "NoEncontrado",
    "obtener_vehiculo_de_otro_conductor": "NoEncontrado",
    "obtener_vehiculo_inexistente": "NoEncontrado",
    "obtener_vehiculo_con_conductor_inexistente": "NoEncontrado",
    "obtener_inexistente": "NoEncontrado",
}

ESTADOS_ESPERADOS = {
    "C_observar_sin_licencia": "OBSERVADA",
    "B_aprobar_con_licencia_que_vence_hoy": "APROBADA",
    "A_aprobar_con_licencia_futura_y_una_vencida": "APROBADA",
    "A_suspender": "SUSPENDIDA",
    "A_volver_a_aprobar": "APROBADA",
    "C_rechazar": "RECHAZADA",
    "C_vehiculo_aprobar_sin_licencia": "APROBADA",
    "C_vehiculo_suspender": "SUSPENDIDA",
    "C_vehiculo_rechazar": "RECHAZADA",
    "A_vehiculo_aprobar": "APROBADA",
}


@pytest.fixture(params=["fake", "sql"])
def resultados(request, uow_sql):
    uow = UnidadDeTrabajoEnMemoria() if request.param == "fake" else uow_sql
    return ejecutar_escenario(uow, RelojFijo(AHORA))


def test_los_errores_del_escenario_son_los_que_pide_la_especificacion(resultados):
    obtenidos = {paso: resultados[paso] for paso in ERRORES_ESPERADOS}

    assert obtenidos == {paso: {"error": nombre} for paso, nombre in ERRORES_ESPERADOS.items()}


def test_los_estados_resultantes_del_escenario_son_los_que_pide_la_especificacion(resultados):
    obtenidos = {paso: resultados[paso]["ok"]["estado"] for paso in ESTADOS_ESPERADOS}

    assert obtenidos == ESTADOS_ESPERADOS


def test_las_licencias_calculan_su_estado_con_el_reloj_y_las_altas_dejan_su_evento(resultados):
    assert resultados["licencia_B_vence_hoy"]["ok"]["estado"] == "VIGENTE"
    assert resultados["licencia_A_vencida"]["ok"]["estado"] == "VENCIDO"
    assert resultados["licencia_A_futura"]["ok"]["estado"] == "VIGENTE"
    assert resultados["historiales_tras_dni_duplicado"] == {
        alias: [
            {
                "accion": "ALTA",
                "anterior": None,
                "nuevo": "PENDIENTE",
                "motivo": "Alta del conductor",
                "operador": None,
                "fecha": AHORA.isoformat(),
            }
        ]
        for alias in ("A", "B", "C")
    }
    assert resultados["dnis_tras_dni_duplicado"] == ["30000001", "30000002", "30000003"]


def test_aprobar_sin_licencia_no_cambia_el_estado_ni_el_historial(resultados):
    assert resultados["C_estado_tras_aprobar_sin_licencia"]["ok"]["estado"] == "PENDIENTE"
    assert [
        e["accion"] for e in resultados["C_estado_tras_aprobar_sin_licencia"]["ok"]["historial"]
    ] == ["ALTA"]


def test_el_historial_de_A_queda_en_orden_con_el_alta_primero(resultados):
    historial = resultados["historial_A"]["ok"]["historial"]

    assert [(e["accion"], e["anterior"], e["nuevo"]) for e in historial] == [
        ("ALTA", None, "PENDIENTE"),
        ("APROBAR", "PENDIENTE", "APROBADA"),
        ("SUSPENDER", "APROBADA", "SUSPENDIDA"),
        ("APROBAR", "SUSPENDIDA", "APROBADA"),
    ]
    assert [e["operador"] for e in historial] == [None, 7, 7, 7]
    assert historial[1]["motivo"] == "Todo en orden"
    assert historial[1]["fecha"] == datetime(2026, 6, 16, 12, 0, tzinfo=UTC).isoformat()
    assert [e["fecha"] for e in historial] == sorted(e["fecha"] for e in historial)


def test_el_vehiculo_nuevo_queda_pendiente_con_servicios_sin_habilitar(resultados):
    vehiculo = resultados["vehiculo_A_auto"]["ok"]["vehiculo"]

    assert vehiculo["habilitacion"] == "PENDIENTE"
    assert vehiculo["servicios"] == [("ENVIOS", False), ("PASAJEROS", False)]
    assert resultados["vehiculo_A_auto"]["ok"]["documentos"] == []


def test_los_filtros_de_conductores_devuelven_los_esperados(resultados):
    def dnis_de(clave):
        return [d["conductor"]["dni"] for d in resultados[clave]["ok"]]

    assert dnis_de("listar_todos") == ["30000001", "30000002", "30000003"]
    assert dnis_de("listar_habilitados") == ["30000001", "30000002"]
    assert dnis_de("listar_no_habilitados") == ["30000003"]
    assert dnis_de("listar_disponibles") == ["30000002"]
    assert dnis_de("listar_no_disponibles") == ["30000001", "30000003"]
    assert dnis_de("listar_con_auto") == ["30000001", "30000002"]
    assert dnis_de("listar_con_moto") == ["30000001", "30000003"]
    assert dnis_de("listar_habilitados_con_moto") == ["30000001"]
    assert dnis_de("listar_habilitados_disponibles_con_auto") == ["30000002"]
    assert dnis_de("listar_sin_coincidencias") == []


def test_los_filtros_de_vehiculos_devuelven_los_esperados(resultados):
    def patentes_de(clave):
        return [v["patente"] for v in resultados[clave]["ok"]]

    assert patentes_de("vehiculos_de_A") == ["AAA111", "BBB222"]
    assert patentes_de("vehiculos_de_A_motos") == ["BBB222"]
    assert patentes_de("vehiculos_de_A_aprobados") == ["AAA111"]
    assert patentes_de("vehiculos_de_A_motos_aprobadas") == []
    assert patentes_de("vehiculos_de_C_rechazados") == ["DDD444"]


# --- Tests solo-SQL: lo que queda en la base ---


def contar(fabrica_sesiones, consulta):
    with fabrica_sesiones() as sesion:
        return sesion.execute(text(consulta)).scalar_one()


def crear_conductor_sql(uow, reloj, dni="30000001"):
    return CrearConductor(uow, reloj).ejecutar(
        dni=dni,
        nombre="Ana",
        apellido="Perez",
        telefono="+54 379 4000000",
        email="ana@example.com",
    )


def test_crear_conductor_persiste_el_conductor_y_su_alta_en_la_base(uow_sql, fabrica_sesiones):
    detalle = crear_conductor_sql(uow_sql, RelojFijo(AHORA))

    assert contar(fabrica_sesiones, "SELECT count(*) FROM conductor") == 1
    assert contar(fabrica_sesiones, "SELECT count(*) FROM habilitacion_evento_conductor") == 1
    assert (
        contar(fabrica_sesiones, "SELECT estado_habilitacion FROM conductor")
        == detalle.conductor.habilitacion.value
    )


def test_un_dni_duplicado_no_deja_restos_en_la_base(uow_sql, fabrica_sesiones):
    reloj = RelojFijo(AHORA)
    crear_conductor_sql(uow_sql, reloj)

    with pytest.raises(DniDuplicado):
        crear_conductor_sql(uow_sql, reloj)

    assert contar(fabrica_sesiones, "SELECT count(*) FROM conductor") == 1
    assert contar(fabrica_sesiones, "SELECT count(*) FROM habilitacion_evento_conductor") == 1


def test_aprobar_sin_licencia_vigente_hace_rollback_real_en_la_base(uow_sql, fabrica_sesiones):
    reloj = RelojFijo(AHORA)
    id_conductor = crear_conductor_sql(uow_sql, reloj).conductor.id

    with pytest.raises(LicenciaVigenteRequerida):
        AccionarHabilitacionConductor(uow_sql, reloj).ejecutar(
            id_conductor=id_conductor, accion=APROBAR, motivo="Intento", id_operador=ID_OPERADOR
        )

    assert contar(fabrica_sesiones, "SELECT estado_habilitacion FROM conductor") == "PENDIENTE"
    assert contar(fabrica_sesiones, "SELECT count(*) FROM habilitacion_evento_conductor") == 1


def test_una_accion_valida_confirma_el_estado_y_el_evento_juntos(uow_sql, fabrica_sesiones):
    reloj = RelojFijo(AHORA)
    id_conductor = crear_conductor_sql(uow_sql, reloj).conductor.id

    AccionarHabilitacionConductor(uow_sql, reloj).ejecutar(
        id_conductor=id_conductor, accion=OBSERVAR, motivo="Falta foto", id_operador=ID_OPERADOR
    )

    assert contar(fabrica_sesiones, "SELECT estado_habilitacion FROM conductor") == "OBSERVADA"
    assert (
        contar(
            fabrica_sesiones,
            "SELECT motivo FROM habilitacion_evento_conductor WHERE accion = 'OBSERVAR'",
        )
        == "Falta foto"
    )
    assert (
        contar(
            fabrica_sesiones,
            "SELECT id_operador FROM habilitacion_evento_conductor WHERE accion = 'OBSERVAR'",
        )
        == ID_OPERADOR
    )


def test_una_patente_duplicada_no_deja_vehiculo_servicios_ni_evento_en_la_base(
    uow_sql, fabrica_sesiones
):
    reloj = RelojFijo(AHORA)
    id_conductor = crear_conductor_sql(uow_sql, reloj).conductor.id
    registrar = RegistrarVehiculo(uow_sql, reloj)
    datos = {
        "id_conductor": id_conductor,
        "tipo": AUTO,
        "patente": "AAA111",
        "marca": "Toyota",
        "modelo": "Etios",
        "anio": 2019,
        "tipos_servicio": [PASAJEROS, ENVIOS],
    }
    registrar.ejecutar(**datos)

    with pytest.raises(PatenteDuplicada):
        registrar.ejecutar(**datos)

    assert contar(fabrica_sesiones, "SELECT count(*) FROM vehiculo") == 1
    assert contar(fabrica_sesiones, "SELECT count(*) FROM vehiculo_tipo_servicio") == 2
    assert contar(fabrica_sesiones, "SELECT count(*) FROM habilitacion_evento_vehiculo") == 1


def test_un_dato_invalido_del_vehiculo_no_persiste_nada(uow_sql, fabrica_sesiones):
    reloj = RelojFijo(AHORA)
    id_conductor = crear_conductor_sql(uow_sql, reloj).conductor.id

    with pytest.raises(DatosInvalidos):
        RegistrarVehiculo(uow_sql, reloj).ejecutar(
            id_conductor=id_conductor,
            tipo=AUTO,
            patente="AAA111",
            marca="Toyota",
            modelo="Etios",
            anio=2019,
            tipos_servicio=[],
        )

    assert contar(fabrica_sesiones, "SELECT count(*) FROM vehiculo") == 0
    assert contar(fabrica_sesiones, "SELECT count(*) FROM habilitacion_evento_vehiculo") == 0


def test_accionar_la_habilitacion_toma_la_fila_con_for_update(
    uow_sql, engine_integracion, fabrica_sesiones
):
    reloj = RelojFijo(AHORA)
    id_conductor = crear_conductor_sql(uow_sql, reloj).conductor.id
    detalle_vehiculo = RegistrarVehiculo(uow_sql, reloj).ejecutar(
        id_conductor=id_conductor,
        tipo=AUTO,
        patente="AAA111",
        marca="Toyota",
        modelo="Etios",
        anio=2019,
        tipos_servicio=[PASAJEROS],
    )

    with capturar_sentencias(engine_integracion) as del_conductor:
        AccionarHabilitacionConductor(uow_sql, reloj).ejecutar(
            id_conductor=id_conductor, accion=OBSERVAR, motivo="Revision", id_operador=ID_OPERADOR
        )
    with capturar_sentencias(engine_integracion) as del_vehiculo:
        AccionarHabilitacionVehiculo(uow_sql, reloj).ejecutar(
            id_conductor=id_conductor,
            id_vehiculo=detalle_vehiculo.vehiculo.id,
            accion=APROBAR,
            motivo="Revision",
            id_operador=ID_OPERADOR,
        )

    assert any("FOR UPDATE" in s.upper() for s in del_conductor)
    assert any("FOR UPDATE" in s.upper() for s in del_vehiculo)
