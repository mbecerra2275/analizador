"""
Tests de CorrelationAnalyzer: agrupación y deduplicación.

Caso central: dos correlation-ids distintos (abc-123, def-456) con el MISMO
error normalizado ("Connection failed" + mismo stack trace) deben fusionarse
en un solo grupo, conservando los ids originales. Un error de distinto tipo
(Timeout) debe quedar en su propio grupo.
"""
from app.core.correlation_analyzer import CorrelationAnalyzer
from app.core.log_parser import LogParser
from tests.conftest import FIXTURES_DIR


def _parse(fixture_name: str):
    """Parsea un fixture y devuelve las entradas."""
    content = (FIXTURES_DIR / fixture_name).read_text(encoding="utf-8")
    return LogParser().parse(content)


def test_errores_identicos_distinto_id_se_fusionan():
    """
    Regresión: abc-123 y def-456 tienen el mismo error → 1 grupo fusionado.

    Fixture: tests/fixtures/duplicates.log (2 Connection failed + 1 Timeout).
    """
    entries = _parse("duplicates.log")
    groups = CorrelationAnalyzer().group_by_correlation(entries)

    error_groups = [g for g in groups if g["has_errors"]]
    # 3 errores de entrada, pero solo 2 patrones únicos de salida.
    assert len(error_groups) == 2

    merged = next(g for g in error_groups if g.get("merged_count", 1) > 1)
    assert merged["merged_count"] == 2
    assert merged["error_count"] == 2
    # Los ids originales se conservan para trazabilidad en el reporte.
    assert set(merged["original_correlation_ids"]) == {"abc-123", "def-456"}


def test_error_distinto_no_se_fusiona():
    """El Timeout (patrón distinto) queda en su propio grupo, sin fusionar."""
    entries = _parse("duplicates.log")
    groups = CorrelationAnalyzer().group_by_correlation(entries)

    timeout_groups = [g for g in groups if g["correlation_id"] == "jkl-012"]
    assert len(timeout_groups) == 1
    assert timeout_groups[0]["has_errors"] is True
    assert timeout_groups[0]["error_count"] == 1
    assert "merged_count" not in timeout_groups[0]


def test_normalizacion_ignora_variables():
    """
    Dos mensajes que solo difieren en variables (timestamps, ids, números)
    producen la misma firma y por tanto se deduplican.
    """
    analyzer = CorrelationAnalyzer()

    msg_a = "2024-01-15 10:30:45 ERROR [abc-123] Connection failed to 10.0.0.5:8080"
    msg_b = "2024-01-15 10:31:02 ERROR [def-456] Connection failed to 10.0.0.9:9090"

    sig_a = analyzer._get_error_signature([{"message": msg_a}])
    sig_b = analyzer._get_error_signature([{"message": msg_b}])

    assert sig_a == sig_b


def test_grupo_sin_errores_no_se_deduplica():
    """Los grupos informativos (sin errores) pasan intactos, sin fusionar."""
    entries = _parse("duplicates.log")
    groups = CorrelationAnalyzer().group_by_correlation(entries)

    info_groups = [g for g in groups if not g["has_errors"]]
    assert len(info_groups) == 1
    assert info_groups[0]["correlation_id"] == "ghi-789"
    assert "merged_count" not in info_groups[0]


def test_entrada_vacia_devuelve_lista_vacia():
    """Caso borde: sin entradas no hay grupos (sin crash)."""
    assert CorrelationAnalyzer().group_by_correlation([]) == []
