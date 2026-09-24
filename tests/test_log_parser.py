"""
Tests de LogParser: detección de formatos y agrupación multilínea.

Cada formato soportado tiene su prueba: si alguien rompe una regex,
el test correspondiente lo señala con precisión.
"""
from app.core.log_parser import LogParser
from tests.conftest import FIXTURES_DIR


def _parse(fixture_name: str):
    content = (FIXTURES_DIR / fixture_name).read_text(encoding="utf-8")
    return LogParser().parse(content)


def test_formato_colon_corr_con_correlation_id():
    """
    Formato 'level: <corr-id-32hex> <timestamp-ISO> mensaje +duración'.

    Es el formato real de los logs del usuario (ver elegibilidad.log).
    """
    entries = _parse("elegibilidad.log")

    assert len(entries) == 9

    with_corr = [e for e in entries if e["correlation_id"]]
    without_corr = [e for e in entries if not e["correlation_id"]]
    # Líneas 2-7 llevan correlation-id; líneas 1, 8 y 9 no.
    assert len(with_corr) == 6
    assert len(without_corr) == 3

    # El correlation-id de 32 hex se extrae intacto.
    assert with_corr[0]["correlation_id"] == "91231791d41e401d832693caba2f603a"
    # Niveles en minúscula ("error:") se normalizan a mayúsculas.
    assert with_corr[0]["level"] == "INFO"


def test_timestamp_iso_con_milisegundos():
    """El timestamp '2026-09-21T17:21:27.575Z' se parsea a datetime."""
    entries = _parse("elegibilidad.log")

    assert entries[0]["timestamp"] is not None
    assert entries[0]["timestamp"].year == 2026
    assert entries[0]["timestamp"].month == 9
    assert entries[0]["timestamp"].day == 21


def test_lineas_de_formato_minoritario_conservan_timestamp():
    """
    Regresión: las líneas cuyo formato NO es el mayoritario detectado
    deben parsearse con su propio patrón, no caer al fallback genérico.

    En elegibilidad.log el formato detectado es colon_corr (6 líneas), pero
    las líneas 1, 8 y 9 son colon_simple: antes perdían timestamp (None)
    y la línea 9 perdía además su nivel ERROR.
    """
    entries = _parse("elegibilidad.log")

    # Ninguna entrada pierde su timestamp.
    assert all(e["timestamp"] is not None for e in entries)

    # La línea del HTTP 500 conserva nivel ERROR.
    # Nota: `message` contiene la línea cruda completa (el parser reescribe
    # message con las líneas originales al cerrar cada entrada para no
    # perder evidencia para la IA/reportes); timestamp, nivel y
    # correlation-id viajan en sus propios campos.
    err_500 = next(e for e in entries if '"code":500' in e["message"])
    assert err_500["level"] == "ERROR"
    assert err_500["message"].endswith("+769ms")


def test_stack_trace_multilinea_una_sola_entrada():
    """
    Un error Java con stack trace (4 líneas físicas) es UNA entrada lógica.

    Las líneas que no empiezan con timestamp se anexan al mensaje de la
    entrada en curso en vez de parsearse por separado.
    """
    entries = _parse("multiline.log")

    npe = next(e for e in entries if "NullPointerException" in e["message"])
    assert npe["multiline"] is True
    assert "at com.app.Handler.process" in npe["message"]
    assert "at java.base/java.lang.Thread.run" in npe["message"]
    # La entrada conserva su nº de línea inicial para trazabilidad.
    assert npe["line_number"] == 1


def test_linea_suelta_sin_timestamp_no_se_pierde():
    """Una línea de continuación (ej: query SQL) no se descarta."""
    entries = _parse("multiline.log")

    # 4 entradas con timestamp + 0 perdidas: todo el contenido queda
    # cubierto por alguna entrada (la query SQL va anexada al WARN).
    assert len(entries) == 4
    warn = next(e for e in entries if e["level"] == "WARN")
    assert "select * from users" in warn["message"]


def test_formato_standard_simple():
    """
    Formato 'YYYY-MM-DD HH:MM:SS LEVEL: mensaje' (colon estilo Syslog).

    Regresión: antes el ':' tras el nivel impedía el match y todo caía
    a nivel INFO por defecto. Ahora el nivel se extrae correctamente.
    """
    entries = _parse("standard.log")

    assert len(entries) == 7
    errors = [e for e in entries if e["level"] == "ERROR"]
    assert len(errors) == 3
    # message conserva la línea cruda (ver nota en el test de regresión
    # de formato minoritario), así que se verifica por sufijo.
    assert errors[0]["message"].endswith("Database connection failed")


def test_contenido_vacio_devuelve_lista_vacia():
    """Contenido vacío o solo espacios → [] sin excepciones."""
    parser = LogParser()
    assert parser.parse("") == []
    assert parser.parse("   \n  \n") == []


def test_cada_entrada_lleva_numero_de_linea():
    """Todas las entradas llevan line_number 1-based para el reporte."""
    entries = _parse("standard.log")

    assert [e["line_number"] for e in entries] == [1, 2, 3, 4, 5, 6, 7]
