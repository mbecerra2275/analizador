"""
Test dorado del pipeline completo (parseo → correlación → filtro → reporte).

Usa el log real de elegibilidad (9 líneas, formato colon_corr) y congela
los valores verificados manualmente. Si cualquier etapa cambia su
comportamiento (un nuevo formato, otra regla de deduplicación, etc.),
este test falla y obliga a revisar si el cambio fue intencional.

La IA está desactivada por el fixture `offline_ollama` de conftest.py:
se verifica la rama 'offline' sin necesidad de Ollama corriendo.
"""
from pathlib import Path

from app.services.analysis_service import AnalysisService
from tests.conftest import fixture_path


def test_pipeline_elegibilidad_valores_congelados(tmp_config):
    """
    Golden test: el log de elegibilidad debe producir SIEMPRE estos valores.

    Fixture: tests/fixtures/elegibilidad.log
    - 9 líneas, 7 con correlation-id 9123... y 2 sin él.
    - 2 errores en el grupo correlacionado + 1 error suelto (HTTP 500).
    """
    service = AnalysisService(tmp_config)
    result = service.analyze_file(fixture_path("elegibilidad.log"))

    # Sin 'error': el análisis no debe fallar.
    assert "error" not in result

    # Valores congelados (verificados manualmente el 2026-09-23).
    # Nota: total_groups es 2 (no 3) desde que el parser conserva los
    # timestamps de las líneas minoritarias: las 3 líneas sin
    # correlation-id comparten minuto (17:21) y forman UN solo grupo
    # temporal en vez de fragmentarse. Ver test de regresión en
    # test_log_parser.py::test_lineas_de_formato_minoritario_conservan_timestamp.
    assert result["total_logs"] == 9
    assert result["total_groups"] == 2
    assert result["filtered_groups"] == 2  # Nada es ruido en este log
    assert len(result["errors"]) == 2


def test_pipeline_grupo_correlacionado_primero(tmp_config):
    """El grupo con más errores va primero (orden desc por error_count)."""
    service = AnalysisService(tmp_config)
    result = service.analyze_file(fixture_path("elegibilidad.log"))

    first, second = result["errors"]

    assert first["correlation_id"] == "91231791d41e401d832693caba2f603a"
    assert first["error_count"] == 2
    assert len(first["messages"]) == 2

    # El error suelto (HTTP 500) queda en su propio grupo.
    assert second["error_count"] == 1
    assert any("500" in m for m in second["messages"])


def test_pipeline_sin_ia_usa_rama_offline(tmp_config):
    """Sin Ollama, el pipeline degrada a 'offline' sin romper el reporte."""
    service = AnalysisService(tmp_config)
    result = service.analyze_file(fixture_path("elegibilidad.log"))

    ai = result["ai_analysis"]
    assert ai["status"] == "offline"
    assert ai["errors_analyzed"] == 2
    # Aun sin IA hay recomendaciones por reglas (fallback).
    assert len(result["recommendations"]) > 0


def test_pipeline_genera_reporte_md_y_html(tmp_config):
    """El análisis genera ambos archivos de reporte en REPORTS_DIR."""
    service = AnalysisService(tmp_config)
    result = service.analyze_file(fixture_path("elegibilidad.log"))

    md_path = Path(result["report_path"])
    html_path = md_path.with_suffix(".html")

    assert md_path.suffix == ".md"
    assert md_path.exists()
    assert html_path.exists()
    # El HTML no debe quedar vacío.
    assert html_path.stat().st_size > 1000
    # Los reportes caen en el temporal, no en output/ del proyecto.
    assert str(tmp_config.REPORTS_DIR) in str(md_path)


def test_pipeline_archivo_inexistente_no_crashea(tmp_config):
    """Archivo inexistente → dict de error, no excepción."""
    service = AnalysisService(tmp_config)
    result = service.analyze_file("no_existe_este_archivo.log")

    assert "error" in result
    assert result["total_logs"] == 0
    assert result["errors"] == []
