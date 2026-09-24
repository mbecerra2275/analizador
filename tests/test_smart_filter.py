"""
Tests de SmartFilter: qué se conserva y qué se descarta.

El filtro existe para que el ruido operativo de Kubernetes (probes,
métricas, heartbeats) no llegue a la IA ni infle las métricas.
"""
from app.core.smart_filter import SmartFilter


def _group(messages, has_errors=False, count=None):
    """Construye un grupo mínimo para probar el filtro."""
    return {
        "correlation_id": "test-id",
        "entries": [{"message": m} for m in messages],
        "error_messages": [m for m in messages] if has_errors else [],
        "count": count if count is not None else len(messages),
        "has_errors": has_errors,
    }


def test_grupo_con_errores_siempre_pasa():
    """Un grupo con errores nunca se descarta, aunque mencione ruido."""
    groups = [_group(["ERROR connection refused"], has_errors=True)]
    assert len(SmartFilter().filter_groups(groups)) == 1


def test_health_check_se_descarta():
    """Ruido típico de Kubernetes (probes, heartbeats) se filtra."""
    noise = [
        "liveness probe failed: connection refused",  # Ojo: contiene 'failed'
        "readiness probe succeeded",
        "heartbeat received from node-1",
        "scraping metrics from prometheus",
        "garbage collection completed",
    ]
    groups = [_group([msg]) for msg in noise]
    assert SmartFilter().filter_groups(groups) == []


def test_mensaje_normal_se_conserva():
    """Un mensaje informativo normal no es ruido y se conserva."""
    groups = [_group(["Request: proceso DATACARD_EFICIENCIA completado"])]
    assert len(SmartFilter().filter_groups(groups)) == 1


def test_grupo_grande_por_volumen_se_conserva():
    """Grupo sin errores pero con >10 logs pasa por volumen anómalo."""
    groups = [_group(["heartbeat ok"] * 11)]
    assert len(SmartFilter().filter_groups(groups)) == 1


def test_lista_vacia_no_falla():
    assert SmartFilter().filter_groups([]) == []
    assert SmartFilter().filter_entries([]) == []


def test_filter_entries_conserva_errores_y_descarta_ruido():
    """A nivel entrada: ERROR siempre pasa, INFO con ruido no."""
    entries = [
        {"level": "ERROR", "message": "Timeout connecting to API"},
        {"level": "INFO", "message": "heartbeat received"},
        {"level": "INFO", "message": "Consulta TBL_DATOS_MAESTROS_SOC OK"},
    ]
    result = SmartFilter().filter_entries(entries)

    assert len(result) == 2
    assert result[0]["level"] == "ERROR"
    assert "heartbeat" not in result[1]["message"]
