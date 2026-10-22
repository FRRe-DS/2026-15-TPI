"""Documento del conductor (licencia).

Firmas bajo prueba:
    Documento.crear(tipo, numero, categoria, fecha_emision, fecha_vencimiento, url_archivo)
    documento.estado_al(hoy) -> EstadoDocumento  (el estado no se guarda: se calcula)
"""

from datetime import date, timedelta

import pytest
from app.dominio.documento import Documento, EstadoDocumento, TipoDocumento
from app.dominio.errores import DatosInvalidos

HOY = date(2026, 6, 15)


def crear(**cambios):
    datos = {
        "tipo": TipoDocumento.LICENCIA,
        "numero": "LIC-123456",
        "categoria": "B1",
        "fecha_emision": date(2024, 1, 10),
        "fecha_vencimiento": date(2029, 1, 10),
        "url_archivo": "https://almacen.example.com/licencias/lic-123456.pdf",
    }
    datos.update(cambios)
    return Documento.crear(**datos)


@pytest.mark.parametrize(
    ("fecha_vencimiento", "estado_esperado"),
    [
        (HOY + timedelta(days=1), EstadoDocumento.VIGENTE),
        (HOY, EstadoDocumento.VIGENTE),
        (HOY - timedelta(days=1), EstadoDocumento.VENCIDO),
    ],
    ids=["vence_manana", "vence_hoy", "vencio_ayer"],
)
def test_estado_se_calcula_segun_la_fecha_de_hoy(fecha_vencimiento, estado_esperado):
    documento = crear(fecha_emision=date(2020, 1, 1), fecha_vencimiento=fecha_vencimiento)

    assert documento.estado_al(HOY) is estado_esperado


def test_el_mismo_documento_pasa_de_vigente_a_vencido_al_avanzar_la_fecha():
    documento = crear(fecha_vencimiento=HOY)

    assert documento.estado_al(HOY) is EstadoDocumento.VIGENTE
    assert documento.estado_al(HOY + timedelta(days=1)) is EstadoDocumento.VENCIDO


@pytest.mark.parametrize(
    "fecha_vencimiento",
    [date(2024, 1, 10), date(2023, 12, 31)],
    ids=["igual_a_emision", "anterior_a_emision"],
)
def test_rechaza_vencimiento_no_posterior_a_la_emision(fecha_vencimiento):
    with pytest.raises(DatosInvalidos):
        crear(fecha_emision=date(2024, 1, 10), fecha_vencimiento=fecha_vencimiento)


def test_crea_documento_de_tipo_licencia():
    assert crear(tipo=TipoDocumento.LICENCIA).tipo is TipoDocumento.LICENCIA


def test_acepta_url_de_archivo_con_esquema_y_host():
    url = "https://almacen.example.com/licencias/lic-123456.pdf"

    assert crear(url_archivo=url).url_archivo == url


@pytest.mark.parametrize(
    "url_archivo",
    ["abc", "", "   ", "https://", "licencia.pdf", "/licencias/lic-123456.pdf"],
)
def test_rechaza_url_de_archivo_invalida(url_archivo):
    with pytest.raises(DatosInvalidos):
        crear(url_archivo=url_archivo)


@pytest.mark.parametrize("numero", ["", "   "])
def test_rechaza_numero_vacio(numero):
    with pytest.raises(DatosInvalidos):
        crear(numero=numero)


def test_la_categoria_es_opcional():
    assert crear(categoria=None).categoria is None
