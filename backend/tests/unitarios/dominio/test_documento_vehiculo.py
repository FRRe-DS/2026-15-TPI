"""Documento del vehiculo (US6).

Firmas bajo prueba:
    DocumentoVehiculo.crear(tipo, numero, entidad_emisora, fecha_emision,
                            fecha_vencimiento, url_archivo)
    documento.estado_al(hoy) -> EstadoDocumento  (el estado no se guarda: se calcula)

Reutiliza `EstadoDocumento` del documento del conductor.
"""

from datetime import date, timedelta

import pytest
from app.dominio.documento import EstadoDocumento
from app.dominio.documento_vehiculo import DocumentoVehiculo, TipoDocumentoVehiculo
from app.dominio.errores import DatosInvalidos

HOY = date(2026, 6, 15)


def crear(**cambios):
    datos = {
        "tipo": TipoDocumentoVehiculo.SEGURO,
        "numero": "SEG-123456",
        "entidad_emisora": "Aseguradora Ejemplo",
        "fecha_emision": date(2024, 1, 10),
        "fecha_vencimiento": date(2029, 1, 10),
        "url_archivo": "https://almacen.example.com/vehiculos/seguro.pdf",
    }
    datos.update(cambios)
    return DocumentoVehiculo.crear(**datos)


@pytest.mark.parametrize(
    "tipo",
    [
        TipoDocumentoVehiculo.SEGURO,
        TipoDocumentoVehiculo.CEDULA_VERDE,
        TipoDocumentoVehiculo.VTV,
    ],
)
def test_acepta_los_tres_tipos_de_documento_de_vehiculo(tipo):
    assert crear(tipo=tipo).tipo is tipo


@pytest.mark.parametrize("numero", ["", "   "])
def test_rechaza_numero_vacio(numero):
    with pytest.raises(DatosInvalidos):
        crear(numero=numero)


def test_la_entidad_emisora_es_opcional():
    assert crear(entidad_emisora=None).entidad_emisora is None


@pytest.mark.parametrize(
    "fecha_vencimiento",
    [date(2024, 1, 10), date(2023, 12, 31)],
    ids=["igual_a_emision", "anterior_a_emision"],
)
def test_rechaza_vencimiento_no_posterior_a_la_emision(fecha_vencimiento):
    with pytest.raises(DatosInvalidos):
        crear(fecha_emision=date(2024, 1, 10), fecha_vencimiento=fecha_vencimiento)


def test_acepta_vencimiento_posterior_a_la_emision():
    documento = crear()

    assert documento.fecha_vencimiento == date(2029, 1, 10)


def test_acepta_url_de_archivo_con_esquema_y_host():
    url = "https://almacen.example.com/vehiculos/vtv.pdf"

    assert crear(url_archivo=url).url_archivo == url


@pytest.mark.parametrize(
    "url_archivo",
    ["abc", "", "   ", "https://", "vtv.pdf", "/vehiculos/vtv.pdf"],
)
def test_rechaza_url_de_archivo_invalida(url_archivo):
    with pytest.raises(DatosInvalidos):
        crear(url_archivo=url_archivo)


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
