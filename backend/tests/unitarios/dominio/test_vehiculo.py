"""Vehiculo del conductor.

Firma bajo prueba:
    Vehiculo.crear(*, tipo: TipoVehiculo, patente, marca, modelo, anio: int,
                   tipos_servicio: list[TipoServicio]) -> Vehiculo
El vehiculo expone: tipo, patente, marca, modelo, anio, habilitacion y
tipos_servicio, una lista de objetos con `.tipo` (TipoServicio) y `.habilitado`.
"""

import pytest
from app.dominio.errores import DatosInvalidos
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.vehiculo import TipoServicio, TipoVehiculo, Vehiculo


def crear(**cambios):
    datos = {
        "tipo": TipoVehiculo.AUTO,
        "patente": "AB123CD",
        "marca": "Toyota",
        "modelo": "Etios",
        "anio": 2019,
        "tipos_servicio": [TipoServicio.PASAJEROS],
    }
    datos.update(cambios)
    return Vehiculo.crear(**datos)


@pytest.mark.parametrize("tipo", [TipoVehiculo.AUTO, TipoVehiculo.MOTO])
def test_acepta_tipo_auto_o_moto(tipo):
    assert crear(tipo=tipo).tipo is tipo


def test_rechaza_tipo_de_vehiculo_desconocido():
    with pytest.raises(DatosInvalidos):
        crear(tipo="CAMION")


@pytest.mark.parametrize(
    "tipos_servicio",
    [
        [TipoServicio.PASAJEROS],
        [TipoServicio.ENVIOS],
        [TipoServicio.PASAJEROS, TipoServicio.ENVIOS],
    ],
    ids=["solo_pasajeros", "solo_envios", "ambos"],
)
def test_acepta_uno_o_mas_tipos_de_servicio_distintos(tipos_servicio):
    vehiculo = crear(tipos_servicio=tipos_servicio)

    assert {servicio.tipo for servicio in vehiculo.tipos_servicio} == set(tipos_servicio)
    assert len(vehiculo.tipos_servicio) == len(tipos_servicio)


def test_rechaza_lista_vacia_de_tipos_de_servicio():
    with pytest.raises(DatosInvalidos):
        crear(tipos_servicio=[])


def test_rechaza_tipos_de_servicio_repetidos():
    with pytest.raises(DatosInvalidos):
        crear(tipos_servicio=[TipoServicio.ENVIOS, TipoServicio.ENVIOS])


def test_vehiculo_nuevo_queda_pendiente_con_todos_sus_servicios_sin_habilitar():
    vehiculo = crear(tipos_servicio=[TipoServicio.PASAJEROS, TipoServicio.ENVIOS])

    assert vehiculo.habilitacion is EstadoHabilitacion.PENDIENTE
    assert [servicio.habilitado for servicio in vehiculo.tipos_servicio] == [
        False,
        False,
    ]


@pytest.mark.parametrize("campo", ["patente", "marca", "modelo"])
@pytest.mark.parametrize("valor", ["", "   "])
def test_rechaza_campos_obligatorios_vacios(campo, valor):
    with pytest.raises(DatosInvalidos):
        crear(**{campo: valor})


def test_acepta_anio_entero():
    assert crear(anio=2021).anio == 2021


@pytest.mark.parametrize("anio", ["2020", 2020.5, None], ids=["texto", "decimal", "nulo"])
def test_rechaza_anio_que_no_es_entero(anio):
    with pytest.raises(DatosInvalidos):
        crear(anio=anio)
