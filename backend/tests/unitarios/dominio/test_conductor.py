from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app.dominio.conductor import Conductor, EstadoConductor
from app.dominio.errores import DatosInvalidos
from app.dominio.habilitacion import EstadoHabilitacion

AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)


def crear(**cambios):
    datos = {
        "dni": "30123456",
        "nombre": "Ana",
        "apellido": "Pérez",
        "telefono": "+54 379 4000000",
        "email": "ana@example.com",
    }
    datos.update(cambios)
    return Conductor.crear(**datos)


@pytest.mark.parametrize("dni", ["1234567", "12345678"])
def test_acepta_dni_de_7_u_8_digitos(dni):
    assert crear(dni=dni).dni == dni


@pytest.mark.parametrize("dni", ["1234567a", "123456", "123456789", "", "12 34567", "١٢٣٤٥٦٧"])
def test_rechaza_dni_invalido(dni):
    with pytest.raises(DatosInvalidos):
        crear(dni=dni)


@pytest.mark.parametrize("campo", ["nombre", "apellido", "telefono"])
@pytest.mark.parametrize("valor", ["", "   "])
def test_rechaza_campos_obligatorios_vacios(campo, valor):
    with pytest.raises(DatosInvalidos):
        crear(**{campo: valor})


@pytest.mark.parametrize("email", ["sin-arroba", "a@", "@b.com", "a b@c.com", ""])
def test_rechaza_email_con_formato_invalido(email):
    with pytest.raises(DatosInvalidos):
        crear(email=email)


def test_conductor_nuevo_queda_pendiente_y_sin_conexion():
    conductor = crear()

    assert conductor.habilitacion is EstadoHabilitacion.PENDIENTE
    assert conductor.estado is EstadoConductor.DESCONECTADO


def test_conductor_nuevo_queda_desconectado_y_sin_estado_ni_puntajes():
    conductor = crear()

    assert conductor.estado is EstadoConductor.DESCONECTADO
    assert conductor.id_vehiculo_activo is None
    assert conductor.fecha_ultimo_cambio_estado is None
    assert conductor.suma_puntajes == 0
    assert conductor.cantidad_calificaciones == 0
    assert conductor.puntaje_promedio is None


@pytest.mark.parametrize(
    ("suma", "cantidad", "esperado"),
    [
        (14, 3, Decimal("4.67")),
        (9, 2, Decimal("4.50")),
        (1, 8, Decimal("0.13")),
        (0, 3, Decimal("0.00")),
    ],
)
def test_puntaje_promedio_es_suma_sobre_cantidad_en_dos_decimales_mitad_arriba(
    suma, cantidad, esperado
):
    conductor = crear()
    conductor.suma_puntajes = suma
    conductor.cantidad_calificaciones = cantidad

    assert conductor.puntaje_promedio == esperado


@pytest.mark.parametrize(
    ("suma", "cantidad"),
    [(-1, 1), (10, -1), (1, 0)],
    ids=["suma-negativa", "cantidad-negativa", "cantidad-cero-con-suma"],
)
def test_puntaje_promedio_rechaza_totales_invalidos(suma, cantidad):
    conductor = crear()
    conductor.suma_puntajes = suma
    conductor.cantidad_calificaciones = cantidad

    with pytest.raises(DatosInvalidos):
        _ = conductor.puntaje_promedio


def test_fijar_ubicacion_guarda_las_coordenadas_y_la_fecha():
    conductor = crear()

    conductor.fijar_ubicacion(-31.4, -64.2, AHORA)

    assert conductor.latitud == -31.4
    assert conductor.longitud == -64.2
    assert conductor.fecha_act_ubic == AHORA
    assert conductor.tiene_ubicacion is True


@pytest.mark.parametrize(
    ("latitud", "longitud"),
    [
        (-90, -180),
        (-90, 180),
        (90, -180),
        (90, 180),
        (0, 0),
    ],
)
def test_fijar_ubicacion_acepta_los_limites_del_rango(latitud, longitud):
    conductor = crear()

    conductor.fijar_ubicacion(latitud, longitud, AHORA)

    assert conductor.latitud == latitud
    assert conductor.longitud == longitud


@pytest.mark.parametrize(
    ("latitud", "longitud"),
    [
        (-90.1, 0),
        (90.1, 0),
        (0, -180.1),
        (0, 180.1),
    ],
    ids=["latitud-baja", "latitud-alta", "longitud-baja", "longitud-alta"],
)
def test_fijar_ubicacion_rechaza_coordenadas_fuera_de_rango(latitud, longitud):
    conductor = crear()

    with pytest.raises(DatosInvalidos):
        conductor.fijar_ubicacion(latitud, longitud, AHORA)

    assert conductor.latitud is None
    assert conductor.longitud is None
    assert conductor.fecha_act_ubic is None
    assert conductor.tiene_ubicacion is False


def test_tiene_ubicacion_es_falso_sin_coordenadas_ni_fecha():
    assert crear().tiene_ubicacion is False


def test_tiene_ubicacion_es_falso_con_coordenadas_incompletas():
    solo_latitud = crear()
    solo_latitud.latitud = -31.4
    solo_longitud = crear()
    solo_longitud.longitud = -64.2

    assert solo_latitud.tiene_ubicacion is False
    assert solo_longitud.tiene_ubicacion is False
