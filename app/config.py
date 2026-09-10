"""
Configuración centralizada de la aplicación.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class Config:
    """Configuración de la aplicación."""
    
    # Rutas
    BASE_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    LOGS_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent / "logs")
    OUTPUT_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent / "output")
    REPORTS_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent / "output" / "reports")
    RULES_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent / "config" / "rules")
    
    # Configuración de Ollama - TIME OUTS MÁS LARGOS
    OLLAMA_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:1.5b"
    OLLAMA_TIMEOUT: int = 120  # Aumentado de 45 a 120 segundos
    OLLAMA_CONNECTION_TIMEOUT: int = 15
    OLLAMA_READ_TIMEOUT: int = 105
    
    # Reintentos - MENOS REINTENTOS PERO MÁS ESPERA
    OLLAMA_MAX_RETRIES: int = 3  # Reducido de 5 a 3
    OLLAMA_RETRY_DELAY: int = 3
    OLLAMA_BACKOFF_MULTIPLIER: int = 2
    
    # Configuración de modelo - MÁS RÁPIDO
    OLLAMA_TEMPERATURE: float = 0.3
    OLLAMA_NUM_PREDICT: int = 300  # Reducido de 500 a 300
    OLLAMA_TOP_P: float = 0.9
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Path = field(default_factory=lambda: Path(__file__).parent.parent / "logs" / "analyzer.log")
    
    def __post_init__(self):
        """Crea los directorios necesarios y carga variables de entorno."""
        for dir_path in [self.LOGS_DIR, self.OUTPUT_DIR, self.REPORTS_DIR, self.RULES_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        self._load_from_env()
    
    def _load_from_env(self):
        """Carga configuración desde variables de entorno."""
        env_mappings = {
            'OLLAMA_URL': 'OLLAMA_URL',
            'OLLAMA_MODEL': 'OLLAMA_MODEL',
            'OLLAMA_TIMEOUT': 'OLLAMA_TIMEOUT',
            'OLLAMA_MAX_RETRIES': 'OLLAMA_MAX_RETRIES',
            'LOG_LEVEL': 'LOG_LEVEL'
        }
        
        for attr, env_var in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                if attr in ['OLLAMA_TIMEOUT', 'OLLAMA_MAX_RETRIES']:
                    try:
                        setattr(self, attr, int(value))
                    except ValueError:
                        pass
                else:
                    setattr(self, attr, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la configuración a diccionario."""
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

config = Config()