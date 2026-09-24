"""
Fixtures compartidos para los tests.

Principio: los tests unitarios no tocan la red. Ollama es un servicio
externo, así que se desactiva por defecto en todos los tests mediante
`offline_ollama` (autouse). El test que quiera probar la IA de verdad
puede desactivar el mock explícitamente.
"""
from pathlib import Path

import pytest

from app.ai.ollama_client import OllamaClient
from app.config import Config

# Directorio con los logs de ejemplo (autocontenidos, no dependen de
# archivos fuera de tests/).
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def offline_ollama(monkeypatch):
    """
    Desactiva Ollama en todos los tests (no hay llamadas de red).

    Monkeypatchea OllamaClient.is_available para que devuelva False:
    el pipeline toma entonces la rama 'offline'/'fallback' sin intentar
    sockets ni HTTP. Rápido y hermético.
    """
    monkeypatch.setattr(OllamaClient, "is_available", lambda self: False)


@pytest.fixture()
def tmp_config(tmp_path, monkeypatch):
    """
    Config con directorios de salida redirigidos a un temporal de pytest.

    Así el test dorado puede generar reportes reales (.md/.html) sin
    ensuciar output/reports del proyecto. Al terminar, pytest borra tmp_path.
    """
    config = Config()
    # Redirigir solo salida; el resto de la config queda intacta.
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path / "output" / "reports")
    monkeypatch.setattr(config, "LOGS_DIR", tmp_path / "logs")
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return config


def fixture_path(name: str) -> str:
    """Ruta absoluta a un log de ejemplo en tests/fixtures/."""
    return str(FIXTURES_DIR / name)
