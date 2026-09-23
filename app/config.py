"""
Configuración centralizada de la aplicación.
"""
import os                 # Leer variables de entorno
import sys                # Detectar ejecutable PyInstaller (frozen)
from pathlib import Path  # Manejo portable de rutas
from typing import Dict, Any, Optional  # Tipado de retornos
from dataclasses import dataclass, field  # Clase de datos y campos con default


def _get_data_dir() -> Path:
    """
    Directorio escribible para datos de usuario (reportes, logs, reglas).

    La versión instalada vive en "C:\\Program Files\\...", que es de solo
    lectura para usuarios estándar. Por eso, cuando la app corre como
    ejecutable PyInstaller (sys.frozen), los datos van a %LOCALAPPDATA%.
    En modo desarrollo se usa la raíz del proyecto.
    """
    if getattr(sys, 'frozen', False):
        base = os.getenv('LOCALAPPDATA')
        if base:
            return Path(base) / "Log Analyzer IA"
        return Path.home() / "Log Analyzer IA"
    return Path(__file__).parent.parent


@dataclass
class Config:
    """Configuración de la aplicación."""

    # --- Rutas base del proyecto ---
    BASE_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    DATA_DIR: Path = field(default_factory=_get_data_dir)
    LOGS_DIR: Path = field(default_factory=lambda: _get_data_dir() / "logs")
    OUTPUT_DIR: Path = field(default_factory=lambda: _get_data_dir() / "output")
    REPORTS_DIR: Path = field(default_factory=lambda: _get_data_dir() / "output" / "reports")
    RULES_DIR: Path = field(default_factory=lambda: _get_data_dir() / "rules")

    # --- Configuración de Ollama - TIME OUTS MÁS LARGOS ---
    OLLAMA_URL: str = "http://127.0.0.1:11434"          # Endpoint local de Ollama
    OLLAMA_MODEL: str = "qwen2.5-coder:1.5b"            # Modelo a usar
    OLLAMA_TIMEOUT: int = 120                           # Timeout total (de 45 a 120s)
    OLLAMA_CONNECTION_TIMEOUT: int = 15                 # Timeout de conexión
    OLLAMA_READ_TIMEOUT: int = 105                      # Timeout de lectura

    # --- Reintentos - MENOS REINTENTOS PERO MÁS ESPERA ---
    OLLAMA_MAX_RETRIES: int = 3                         # Intentos (de 5 a 3)
    OLLAMA_RETRY_DELAY: int = 3                         # Espera base entre reintentos
    OLLAMA_BACKOFF_MULTIPLIER: int = 2                  # Multiplicador de backoff

    # --- Configuración de modelo - MÁS RÁPIDO ---
    OLLAMA_TEMPERATURE: float = 0.3                     # Creatividad baja
    OLLAMA_NUM_PREDICT: int = 800                       # Tokens máx (aumentado de 300 para respuestas completas)
    OLLAMA_TOP_P: float = 0.9                           # Muestreo nucleus

    # --- Logging ---
    LOG_LEVEL: str = "INFO"                             # Nivel de log por defecto
    LOG_FILE: Path = field(default_factory=lambda: _get_data_dir() / "logs" / "analyzer.log")

    def __post_init__(self):
        """Crea los directorios necesarios y carga variables de entorno."""
        # Crea cada directorio si no existe (idempotente)
        for dir_path in [self.LOGS_DIR, self.OUTPUT_DIR, self.REPORTS_DIR, self.RULES_DIR]:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except PermissionError as e:
                # Error claro en vez de fallo silencioso: el reporte nunca aparecería
                import logging
                logging.getLogger(__name__).error(
                    f"❌ Sin permiso de escritura en {dir_path}. "
                    f"Ejecuta como administrador o revisa los permisos. Detalle: {e}"
                )
                raise

        # Sobrescribe valores con variables de entorno si existen
        self._load_from_env()

    def _load_from_env(self):
        """Carga configuración desde variables de entorno."""
        # Mapeo: atributo de la clase -> nombre de la variable de entorno
        env_mappings = {
            'OLLAMA_URL': 'OLLAMA_URL',
            'OLLAMA_MODEL': 'OLLAMA_MODEL',
            'OLLAMA_TIMEOUT': 'OLLAMA_TIMEOUT',
            'OLLAMA_MAX_RETRIES': 'OLLAMA_MAX_RETRIES',
            'LOG_LEVEL': 'LOG_LEVEL'
        }

        # Recorre el mapeo y aplica cada variable si está definida
        for attr, env_var in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Los numéricos se convierten a int; el resto se deja como str
                if attr in ['OLLAMA_TIMEOUT', 'OLLAMA_MAX_RETRIES']:
                    try:
                        setattr(self, attr, int(value))
                    except ValueError:
                        pass  # Si no es convertible, se ignora
                else:
                    setattr(self, attr, value)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la configuración a diccionario."""
        # Devuelve solo las claves relevantes para Ollama (no las rutas)
        return {
            'ollama_url': self.OLLAMA_URL,
            'ollama_model': self.OLLAMA_MODEL,
            'ollama_timeout': self.OLLAMA_TIMEOUT,
            'ollama_connection_timeout': self.OLLAMA_CONNECTION_TIMEOUT,
            'ollama_read_timeout': self.OLLAMA_READ_TIMEOUT,
            'ollama_max_retries': self.OLLAMA_MAX_RETRIES,
            'ollama_retry_delay': self.OLLAMA_RETRY_DELAY,
            'ollama_backoff_multiplier': self.OLLAMA_BACKOFF_MULTIPLIER,
            'ollama_temperature': self.OLLAMA_TEMPERATURE,
            'ollama_num_predict': self.OLLAMA_NUM_PREDICT,
            'ollama_top_p': self.OLLAMA_TOP_P
        }


# Instancia única (singleton de facto) reutilizable en toda la app
config = Config()