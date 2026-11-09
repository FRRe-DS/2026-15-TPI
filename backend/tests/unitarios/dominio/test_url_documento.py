"""La URL de un documento solo puede ser http o https."""

import pytest
from app.dominio.documento import es_url_valida


@pytest.mark.parametrize(
    "url",
    ["https://archivos.example/doc.pdf", "http://archivos.example/doc.pdf"],
)
def test_acepta_http_y_https(url: str) -> None:
    assert es_url_valida(url)


@pytest.mark.parametrize(
    "url",
    [
        "ftp://archivos.example/doc.pdf",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "javascript://%0aalert(1)",
        "JAVASCRIPT://%0aalert(1)",
        "data:text/html;base64,PHNjcmlwdD4=",
        "//archivos.example/doc.pdf",
        "archivos.example/doc.pdf",
        "no-es-una-url",
        "https://",
        "",
    ],
)
def test_rechaza_otros_esquemas_y_urls_incompletas(url: str) -> None:
    assert not es_url_valida(url)
