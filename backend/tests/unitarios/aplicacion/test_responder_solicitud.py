"""Caso de uso `responder_solicitud` (POST /solicitudes/{id_solicitud}).

Firmas bajo prueba:
    ResponderSolicitud(uow: UnidadDeTrabajo, reloj: Reloj)
    ResponderSolicitud.ejecutar(*, id_solicitud, respuesta: EstadoSolicitud, hora_rta: datetime,
                                identidad: Identidad) -> Solicitud

`respuesta` es `ACEPTADO` o `RECHAZADO`; `hora_rta` es la hora del cliente y se guarda tal cual,
mientras que el vencimiento lo decide la hora del `Reloj`. Orden: lee la solicitud, aplica la
politica de acceso (el conductor debe ser el duenio; el operador puede responder cualquiera),
bloquea al conductor y despues a la solicitud, y revalida. Al aceptar deja al conductor `OCUPADO`
con `fecha_ultimo_cambio_estado` del `Reloj`; al rechazar no toca su estado. Si falla, no queda
nada persistido.
"""

import copy
from datetime import UTC, datetime, timedelta

import pytest
from app.aplicacion.casos_de_uso.responder_solicitud import ResponderSolicitud
from app.aplicacion.politicas.acceso import (
    ROL_CONDUCTOR,
    ROL_OPERADOR,
    ROL_SERVICIO,
    Identidad,
)
from app.dominio.conductor import Conductor, EstadoConductor
from app.dominio.errores import (
    AccesoProhibido,
    ConductorNoHabilitado,
    DatosInvalidos,
    NoEncontrado,
    RolNoAutorizado,
    SolicitudVencida,
    SolicitudYaRespondida,
)
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.solicitud import EstadoSolicitud, Solicitud
from app.dominio.vehiculo import TipoServicio, TipoVehiculo, Vehiculo

from tests.unitarios.fakes.reloj_fijo import RelojFijo
from tests.unitarios.fakes.repositorios_en_memoria import (
    RepositorioSolicitudesEnMemoria,
    UnidadDeTrabajoEnMemoria,
)

AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
ULTIMO_CAMBIO = AHORA - timedelta(days=3)
VIGENTE_HASTA = AHORA + timedelta(minutes=2)
VENCIDA_DESDE = AHORA - timedelta(minutes=2)
HORA_RTA_DEL_CLIENTE = AHORA - timedelta(seconds=30)
ID_OPERADOR = 7

DESCONECTADO = EstadoConductor.DESCONECTADO
CONECTADO = EstadoConductor.CONECTADO
DISPONIBLE = EstadoConductor.DISPONIBLE
OCUPADO = EstadoConductor.OCUPADO
APROBADA = EstadoHabilitacion.APROBADA
PENDIENTE_HABILITACION = EstadoHabilitacion.PENDIENTE
PENDIENTE = EstadoSolicitud.PENDIENTE
ACEPTADO = EstadoSolicitud.ACEPTADO
RECHAZADO = EstadoSolicitud.RECHAZADO

BLOQUEO_CONDUCTOR = "conductor"
BLOQUEO_SOLICITUD = "solicitud"
HORA_RTA_DE_LA_RESPUESTA_GANADORA = AHORA - timedelta(seconds=45)


class UnidadDeTrabajoQueRegistraBloqueos(UnidadDeTrabajoEnMemoria):
    def __init__(self):
        super().__init__()
        self.bloqueos = []

    def bloquear_conductor(self, id_conductor):
        self.bloqueos.append(BLOQUEO_CONDUCTOR)
        return super().bloquear_conductor(id_conductor)

    def bloquear_solicitud(self, id_solicitud):
        self.bloqueos.append(BLOQUEO_SOLICITUD)
        return super().bloquear_solicitud(id_solicitud)


class RepositorioSolicitudesQueEntregaCopias(RepositorioSolicitudesEnMemoria):
    """Como una lectura sin bloqueo: lo leido no se actualiza si otra transaccion confirma."""

    def obtener(self, id_solicitud):
        return copy.deepcopy(super().obtener(id_solicitud))


class UnidadDeTrabajoDondeOtraRespuestaGano(UnidadDeTrabajoEnMemoria):
    """Entre la lectura sin bloqueo y el bloqueo, otra transaccion acepta y confirma."""

    def __init__(self):
        super().__init__()
        self.solicitudes = RepositorioSolicitudesQueEntregaCopias(self._estado)

    def bloquear_solicitud(self, id_solicitud):
        vigente = self._estado.solicitudes[id_solicitud]
        vigente.estado = vigente.respuesta = ACEPTADO
        vigente.hora_rta = HORA_RTA_DE_LA_RESPUESTA_GANADORA
        self.commit()
        return vigente


@pytest.fixture
def uow():
    return UnidadDeTrabajoQueRegistraBloqueos()


@pytest.fixture
def responder(uow):
    return ResponderSolicitud(uow, RelojFijo(AHORA))


@pytest.fixture
def uow_con_respuesta_ganadora():
    return UnidadDeTrabajoDondeOtraRespuestaGano()


@pytest.fixture
def responder_con_respuesta_ganadora(uow_con_respuesta_ganadora):
    return ResponderSolicitud(uow_con_respuesta_ganadora, RelojFijo(AHORA))


def identidad_de_conductor(id_conductor):
    return Identidad(roles={ROL_CONDUCTOR}, id_conductor=id_conductor)


def identidad_de_operador():
    return Identidad(roles={ROL_OPERADOR}, id_operador=ID_OPERADOR)


def sembrar_conductor(uow, dni="30123456", **atributos):
    conductor = Conductor.crear(
        dni=dni,
        nombre="Ana",
        apellido="Perez",
        telefono="+54 379 4000000",
        email="ana@example.com",
    )
    conductor.habilitacion = APROBADA
    conductor.fecha_ultimo_cambio_estado = ULTIMO_CAMBIO
    for atributo, valor in atributos.items():
        setattr(conductor, atributo, valor)
    guardado = uow.conductores.guardar(conductor)
    uow.commit()
    return guardado


def sembrar_vehiculo(uow, id_conductor, habilitacion=APROBADA, patente="AB123CD"):
    vehiculo = Vehiculo.crear(
        tipo=TipoVehiculo.AUTO,
        patente=patente,
        marca="Toyota",
        modelo="Etios",
        anio=2019,
        tipos_servicio=[TipoServicio.PASAJEROS],
    )
    vehiculo.id_conductor = id_conductor
    vehiculo.habilitacion = habilitacion
    guardado = uow.vehiculos.guardar(vehiculo)
    uow.commit()
    return guardado


def sembrar_conductor_habilitado(uow, estado=CONECTADO, dni="30123456"):
    conductor = sembrar_conductor(uow, dni=dni, estado=estado)
    vehiculo = sembrar_vehiculo(uow, conductor.id, patente=f"AB{dni[-3:]}CD")
    conductor.id_vehiculo_activo = vehiculo.id
    uow.commit()
    return conductor


def sembrar_solicitud(uow, id_conductor, vence_en=VIGENTE_HASTA, estado=PENDIENTE):
    solicitud = Solicitud(id_conductor=id_conductor, vence_en=vence_en, estado=estado)
    guardada = uow.solicitudes.guardar(solicitud)
    uow.commit()
    return guardada


def solicitud_guardada(uow, id_solicitud):
    return uow.solicitudes.obtener(id_solicitud)


def conductor_guardado(uow, id_conductor):
    return uow.conductores.obtener(id_conductor)


def aceptar(responder, solicitud, identidad):
    return responder.ejecutar(
        id_solicitud=solicitud.id,
        respuesta=ACEPTADO,
        hora_rta=HORA_RTA_DEL_CLIENTE,
        identidad=identidad,
    )


def rechazar(responder, solicitud, identidad):
    return responder.ejecutar(
        id_solicitud=solicitud.id,
        respuesta=RECHAZADO,
        hora_rta=HORA_RTA_DEL_CLIENTE,
        identidad=identidad,
    )


def assert_solicitud_sin_responder(uow, id_solicitud):
    guardada = solicitud_guardada(uow, id_solicitud)
    assert guardada.estado is PENDIENTE
    assert guardada.respuesta is None
    assert guardada.hora_rta is None


def assert_conductor_sin_cambios(uow, id_conductor, estado_esperado):
    guardado = conductor_guardado(uow, id_conductor)
    assert guardado.estado is estado_esperado
    assert guardado.fecha_ultimo_cambio_estado == ULTIMO_CAMBIO


# --- T332: aceptar y rechazar ------------------------------------------------------------


def test_aceptar_una_vigente_la_deja_aceptada_con_respuesta_y_hora_del_cliente(uow, responder):
    conductor = sembrar_conductor_habilitado(uow)
    solicitud = sembrar_solicitud(uow, conductor.id)

    resultado = aceptar(responder, solicitud, identidad_de_conductor(conductor.id))

    guardada = solicitud_guardada(uow, solicitud.id)
    assert resultado.id == solicitud.id
    assert resultado.estado is ACEPTADO
    assert guardada.estado is ACEPTADO
    assert guardada.respuesta is ACEPTADO
    assert guardada.hora_rta == HORA_RTA_DEL_CLIENTE


@pytest.mark.parametrize("estado_inicial", [CONECTADO, DISPONIBLE])
def test_aceptar_deja_al_conductor_ocupado_con_la_hora_del_reloj(uow, responder, estado_inicial):
    conductor = sembrar_conductor_habilitado(uow, estado_inicial)
    solicitud = sembrar_solicitud(uow, conductor.id)

    aceptar(responder, solicitud, identidad_de_conductor(conductor.id))

    guardado = conductor_guardado(uow, conductor.id)
    assert guardado.estado is OCUPADO
    assert guardado.fecha_ultimo_cambio_estado == AHORA


def test_aceptar_no_cambia_el_vehiculo_activo_del_conductor(uow, responder):
    conductor = sembrar_conductor_habilitado(uow)
    id_vehiculo_activo = conductor.id_vehiculo_activo
    solicitud = sembrar_solicitud(uow, conductor.id)

    aceptar(responder, solicitud, identidad_de_conductor(conductor.id))

    assert conductor_guardado(uow, conductor.id).id_vehiculo_activo == id_vehiculo_activo


def test_rechazar_una_vigente_la_deja_rechazada_con_respuesta_y_hora_del_cliente(uow, responder):
    conductor = sembrar_conductor_habilitado(uow)
    solicitud = sembrar_solicitud(uow, conductor.id)

    resultado = rechazar(responder, solicitud, identidad_de_conductor(conductor.id))

    guardada = solicitud_guardada(uow, solicitud.id)
    assert resultado.estado is RECHAZADO
    assert guardada.estado is RECHAZADO
    assert guardada.respuesta is RECHAZADO
    assert guardada.hora_rta == HORA_RTA_DEL_CLIENTE


@pytest.mark.parametrize("estado_inicial", [DESCONECTADO, CONECTADO, DISPONIBLE, OCUPADO])
def test_rechazar_no_cambia_el_estado_del_conductor(uow, responder, estado_inicial):
    conductor = sembrar_conductor_habilitado(uow, estado_inicial)
    solicitud = sembrar_solicitud(uow, conductor.id)

    rechazar(responder, solicitud, identidad_de_conductor(conductor.id))

    assert_conductor_sin_cambios(uow, conductor.id, estado_inicial)


def test_una_vencida_lanza_solicitud_vencida_y_no_cambia_nada(uow, responder):
    conductor = sembrar_conductor_habilitado(uow)
    solicitud = sembrar_solicitud(uow, conductor.id, vence_en=VENCIDA_DESDE)

    with pytest.raises(SolicitudVencida):
        aceptar(responder, solicitud, identidad_de_conductor(conductor.id))

    assert_solicitud_sin_responder(uow, solicitud.id)
    assert_conductor_sin_cambios(uow, conductor.id, CONECTADO)


def test_una_vencida_lanza_solicitud_vencida_aunque_la_hora_del_cliente_sea_anterior(
    uow, responder
):
    conductor = sembrar_conductor_habilitado(uow)
    solicitud = sembrar_solicitud(uow, conductor.id, vence_en=VENCIDA_DESDE)
    hora_rta_anterior_al_vencimiento = VENCIDA_DESDE - timedelta(minutes=1)

    with pytest.raises(SolicitudVencida):
        responder.ejecutar(
            id_solicitud=solicitud.id,
            respuesta=RECHAZADO,
            hora_rta=hora_rta_anterior_al_vencimiento,
            identidad=identidad_de_conductor(conductor.id),
        )

    assert_solicitud_sin_responder(uow, solicitud.id)


@pytest.mark.parametrize("estado_previo", [ACEPTADO, RECHAZADO])
@pytest.mark.parametrize("respuesta_nueva", [ACEPTADO, RECHAZADO])
def test_una_ya_respondida_lanza_solicitud_ya_respondida_y_no_cambia_nada(
    uow, responder, estado_previo, respuesta_nueva
):
    conductor = sembrar_conductor_habilitado(uow)
    solicitud = sembrar_solicitud(uow, conductor.id, estado=estado_previo)

    with pytest.raises(SolicitudYaRespondida):
        responder.ejecutar(
            id_solicitud=solicitud.id,
            respuesta=respuesta_nueva,
            hora_rta=HORA_RTA_DEL_CLIENTE,
            identidad=identidad_de_conductor(conductor.id),
        )

    guardada = solicitud_guardada(uow, solicitud.id)
    assert guardada.estado is estado_previo
    assert guardada.hora_rta is None
    assert_conductor_sin_cambios(uow, conductor.id, CONECTADO)


def test_aceptar_dos_veces_la_segunda_ve_la_solicitud_ya_respondida(uow, responder):
    conductor = sembrar_conductor_habilitado(uow)
    solicitud = sembrar_solicitud(uow, conductor.id)
    identidad = identidad_de_conductor(conductor.id)
    aceptar(responder, solicitud, identidad)

    with pytest.raises(SolicitudYaRespondida):
        aceptar(responder, solicitud, identidad)


@pytest.mark.parametrize("estado_inicial", [DESCONECTADO, OCUPADO])
def test_aceptar_con_el_conductor_desconectado_u_ocupado_lanza_no_habilitado(
    uow, responder, estado_inicial
):
    conductor = sembrar_conductor_habilitado(uow, estado_inicial)
    solicitud = sembrar_solicitud(uow, conductor.id)

    with pytest.raises(ConductorNoHabilitado):
        aceptar(responder, solicitud, identidad_de_conductor(conductor.id))

    assert_solicitud_sin_responder(uow, solicitud.id)
    assert_conductor_sin_cambios(uow, conductor.id, estado_inicial)


def test_aceptar_con_el_conductor_sin_habilitacion_aprobada_lanza_no_habilitado(uow, responder):
    conductor = sembrar_conductor_habilitado(uow)
    conductor.habilitacion = PENDIENTE_HABILITACION
    uow.commit()
    solicitud = sembrar_solicitud(uow, conductor.id)

    with pytest.raises(ConductorNoHabilitado):
        aceptar(responder, solicitud, identidad_de_conductor(conductor.id))

    assert_solicitud_sin_responder(uow, solicitud.id)
    assert_conductor_sin_cambios(uow, conductor.id, CONECTADO)


def test_aceptar_con_el_conductor_sin_vehiculo_activo_lanza_no_habilitado(uow, responder):
    conductor = sembrar_conductor(uow, estado=CONECTADO)
    solicitud = sembrar_solicitud(uow, conductor.id)

    with pytest.raises(ConductorNoHabilitado):
        aceptar(responder, solicitud, identidad_de_conductor(conductor.id))

    assert_solicitud_sin_responder(uow, solicitud.id)
    assert_conductor_sin_cambios(uow, conductor.id, CONECTADO)


def test_aceptar_con_el_vehiculo_activo_sin_aprobar_lanza_no_habilitado(uow, responder):
    conductor = sembrar_conductor_habilitado(uow)
    vehiculo = uow.vehiculos.obtener(conductor.id, conductor.id_vehiculo_activo)
    vehiculo.habilitacion = PENDIENTE_HABILITACION
    uow.commit()
    solicitud = sembrar_solicitud(uow, conductor.id)

    with pytest.raises(ConductorNoHabilitado):
        aceptar(responder, solicitud, identidad_de_conductor(conductor.id))

    assert_solicitud_sin_responder(uow, solicitud.id)
    assert_conductor_sin_cambios(uow, conductor.id, CONECTADO)


def test_solicitud_inexistente_lanza_no_encontrado(responder):
    with pytest.raises(NoEncontrado):
        responder.ejecutar(
            id_solicitud=999,
            respuesta=ACEPTADO,
            hora_rta=HORA_RTA_DEL_CLIENTE,
            identidad=identidad_de_operador(),
        )


@pytest.mark.parametrize("respuesta_invalida", [PENDIENTE, EstadoSolicitud.VENCIDA])
def test_una_respuesta_distinta_de_aceptado_o_rechazado_lanza_datos_invalidos(
    uow, responder, respuesta_invalida
):
    conductor = sembrar_conductor_habilitado(uow)
    solicitud = sembrar_solicitud(uow, conductor.id)

    with pytest.raises(DatosInvalidos):
        responder.ejecutar(
            id_solicitud=solicitud.id,
            respuesta=respuesta_invalida,
            hora_rta=HORA_RTA_DEL_CLIENTE,
            identidad=identidad_de_conductor(conductor.id),
        )

    assert_solicitud_sin_responder(uow, solicitud.id)


# --- T333: acceso y orden de bloqueos ----------------------------------------------------


def test_un_conductor_que_no_es_el_duenio_lanza_acceso_prohibido_y_no_cambia_nada(uow, responder):
    duenio = sembrar_conductor_habilitado(uow)
    otro = sembrar_conductor_habilitado(uow, dni="30123457")
    solicitud = sembrar_solicitud(uow, duenio.id)

    with pytest.raises(AccesoProhibido):
        aceptar(responder, solicitud, identidad_de_conductor(otro.id))

    assert_solicitud_sin_responder(uow, solicitud.id)
    assert_conductor_sin_cambios(uow, duenio.id, CONECTADO)
    assert_conductor_sin_cambios(uow, otro.id, CONECTADO)


def test_un_conductor_sin_id_en_el_token_lanza_acceso_prohibido(uow, responder):
    conductor = sembrar_conductor_habilitado(uow)
    solicitud = sembrar_solicitud(uow, conductor.id)
    identidad_sin_id = Identidad(roles={ROL_CONDUCTOR})

    with pytest.raises(AccesoProhibido):
        aceptar(responder, solicitud, identidad_sin_id)

    assert_solicitud_sin_responder(uow, solicitud.id)


def test_el_acceso_se_verifica_antes_de_bloquear(uow, responder):
    duenio = sembrar_conductor_habilitado(uow)
    otro = sembrar_conductor_habilitado(uow, dni="30123457")
    solicitud = sembrar_solicitud(uow, duenio.id)

    with pytest.raises(AccesoProhibido):
        aceptar(responder, solicitud, identidad_de_conductor(otro.id))

    assert uow.bloqueos == []


def test_un_rol_de_solo_lectura_lanza_rol_no_autorizado_y_no_cambia_nada(uow, responder):
    conductor = sembrar_conductor_habilitado(uow)
    solicitud = sembrar_solicitud(uow, conductor.id)

    with pytest.raises(RolNoAutorizado):
        aceptar(responder, solicitud, Identidad(roles={ROL_SERVICIO}))

    assert_solicitud_sin_responder(uow, solicitud.id)
    assert_conductor_sin_cambios(uow, conductor.id, CONECTADO)


def test_el_operador_puede_aceptar_la_solicitud_de_cualquier_conductor(uow, responder):
    conductor = sembrar_conductor_habilitado(uow)
    solicitud = sembrar_solicitud(uow, conductor.id)

    resultado = aceptar(responder, solicitud, identidad_de_operador())

    assert resultado.estado is ACEPTADO
    assert conductor_guardado(uow, conductor.id).estado is OCUPADO


def test_el_operador_puede_rechazar_la_solicitud_de_cualquier_conductor(uow, responder):
    conductor = sembrar_conductor_habilitado(uow)
    solicitud = sembrar_solicitud(uow, conductor.id)

    resultado = rechazar(responder, solicitud, identidad_de_operador())

    assert resultado.estado is RECHAZADO
    assert_conductor_sin_cambios(uow, conductor.id, CONECTADO)


def test_bloquea_primero_al_conductor_y_despues_a_la_solicitud(uow, responder):
    conductor = sembrar_conductor_habilitado(uow)
    solicitud = sembrar_solicitud(uow, conductor.id)

    aceptar(responder, solicitud, identidad_de_conductor(conductor.id))

    assert uow.bloqueos == [BLOQUEO_CONDUCTOR, BLOQUEO_SOLICITUD]


def test_al_rechazar_tambien_bloquea_primero_al_conductor_y_despues_a_la_solicitud(uow, responder):
    conductor = sembrar_conductor_habilitado(uow)
    solicitud = sembrar_solicitud(uow, conductor.id)

    rechazar(responder, solicitud, identidad_de_conductor(conductor.id))

    assert uow.bloqueos == [BLOQUEO_CONDUCTOR, BLOQUEO_SOLICITUD]


# --- Revalidacion tras el bloqueo --------------------------------------------------------

RESPONDER_SEGUN_RESPUESTA = {ACEPTADO: aceptar, RECHAZADO: rechazar}


@pytest.mark.parametrize("respuesta", [ACEPTADO, RECHAZADO])
def test_si_otra_respuesta_gano_antes_del_bloqueo_lanza_solicitud_ya_respondida(
    uow_con_respuesta_ganadora, responder_con_respuesta_ganadora, respuesta
):
    uow = uow_con_respuesta_ganadora
    conductor = sembrar_conductor_habilitado(uow)
    solicitud = sembrar_solicitud(uow, conductor.id)
    responder_segun_respuesta = RESPONDER_SEGUN_RESPUESTA[respuesta]

    with pytest.raises(SolicitudYaRespondida):
        responder_segun_respuesta(
            responder_con_respuesta_ganadora, solicitud, identidad_de_conductor(conductor.id)
        )


@pytest.mark.parametrize("respuesta", [ACEPTADO, RECHAZADO])
def test_si_otra_respuesta_gano_antes_del_bloqueo_no_se_pisa_ni_se_toca_al_conductor(
    uow_con_respuesta_ganadora, responder_con_respuesta_ganadora, respuesta
):
    uow = uow_con_respuesta_ganadora
    conductor = sembrar_conductor_habilitado(uow)
    solicitud = sembrar_solicitud(uow, conductor.id)
    responder_segun_respuesta = RESPONDER_SEGUN_RESPUESTA[respuesta]

    with pytest.raises(SolicitudYaRespondida):
        responder_segun_respuesta(
            responder_con_respuesta_ganadora, solicitud, identidad_de_conductor(conductor.id)
        )

    guardada = solicitud_guardada(uow, solicitud.id)
    assert guardada.estado is ACEPTADO
    assert guardada.respuesta is ACEPTADO
    assert guardada.hora_rta == HORA_RTA_DE_LA_RESPUESTA_GANADORA
    assert_conductor_sin_cambios(uow, conductor.id, CONECTADO)
