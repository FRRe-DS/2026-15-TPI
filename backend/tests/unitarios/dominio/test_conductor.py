import pytest

from app.dominio.conductor import Conductor
from app.dominio.errores import DatosInvalidos
from app.dominio.habilitacion import EstadoHabilitacion


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


@pytest.mark.parametrize(
    "dni", ["1234567a", "123456", "123456789", "", "12 34567", "١٢٣٤٥٦٧"]
)
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
    assert conductor.conectado is False
    assert conductor.disponible is False
