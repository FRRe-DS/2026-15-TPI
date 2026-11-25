"""La medición conserva las excepciones y no cuenta ubicación como cambio operativo."""

from unittest.mock import Mock

import pytest
from app.api import observabilidad as obs


@pytest.fixture
def histogram(monkeypatch):
    monkeypatch.setenv("M3_OTEL_ENABLED", "true")
    meter = Mock()
    monkeypatch.setattr(obs.metrics, "get_meter", lambda _: meter)
    return meter.create_histogram.return_value


def test_exito_solo_despues_del_commit(histogram):
    token = obs.recepcion.set(10.0)
    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(obs, "perf_counter", lambda: 12.0)
            with obs.medir_operacion("registration"):
                histogram.record.assert_not_called()
                # El caso de uso hace commit antes de retornar al adaptador HTTP.
            histogram.record.assert_called_once_with(2.0, {"outcome": "success"})
    finally:
        obs.recepcion.reset(token)


def test_fallo_no_se_convierte_en_alta_exitosa(histogram):
    error = RuntimeError("commit fallido")
    with pytest.raises(RuntimeError) as raised, obs.medir_operacion("registration"):
        raise error
    assert raised.value is error
    assert histogram.record.call_args.args[1] == {"outcome": "error"}


def test_ubicacion_sola_no_mide_cambio_operativo(histogram):
    with obs.medir_operacion("operational_state.update", enabled=False):
        pass
    histogram.record.assert_not_called()


def test_desactivada_no_inicializa_instrumentos(monkeypatch):
    monkeypatch.delenv("M3_OTEL_ENABLED", raising=False)
    meter = Mock()
    monkeypatch.setattr(obs.metrics, "get_meter", meter)
    with obs.medir_operacion("registration"):
        pass
    meter.assert_not_called()
