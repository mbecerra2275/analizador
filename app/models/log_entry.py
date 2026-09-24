"""
Modelo de datos: una línea de log ya parseada.

Es la unidad mínima de información del pipeline: el LogParser convierte
texto plano en objetos LogEntry, y el resto de etapas (correlación, filtro,
análisis IA) trabajan sobre ellos en vez de sobre strings.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum


class LogLevel(Enum):
    """Niveles de severidad estándar de logging, de menor a mayor detalle."""
    INFO = "INFO"      # Información general del flujo normal
    WARN = "WARN"      # Avisos: algo inusual pero no fatal
    ERROR = "ERROR"    # Errores: operaciones fallidas
    DEBUG = "DEBUG"    # Detalle para diagnóstico en desarrollo
    TRACE = "TRACE"    # Traza muy fina (entrada/salida de métodos)


class ErrorSeverity(Enum):
    """Severidad asignada a un error tras clasificarlo (no es el nivel de log)."""
    CRITICAL = "critical"  # Caída del servicio / pérdida de datos
    HIGH = "high"          # Funcionalidad principal afectada
    MEDIUM = "medium"      # Funcionalidad secundaria afectada
    LOW = "low"            # Cosmético o fácilmente recuperable
    INFO = "info"          # Informativo, sin impacto
    UNKNOWN = "unknown"    # Aún sin clasificar (valor por defecto)


@dataclass
class LogEntry:
    """Representa una línea de log parseada y enriquecida con metadatos."""
    timestamp: Optional[datetime]  # Momento del evento (None si no se pudo parsear)
    level: LogLevel                # Nivel de severidad del log
    correlation_id: Optional[str]  # Id que agrupa logs de la misma transacción (None si no hay)
    service: str                   # Microservicio/componente origen (ej: "ms-oferta")
    class_name: str                # Clase Java/Python que emitió el log
    message: str                   # Mensaje ya limpio (sin timestamp ni nivel)
    raw_line: str                  # Línea original intacta (para auditoría y reportes)
    has_error_keyword: bool        # True si el mensaje contiene palabras de error
    error_type: Optional[str] = None          # Categoría detectada (timeout, conexion, ...)
    stack_trace: Optional[str] = None         # Traza apilada si era un error multilínea
    severity: ErrorSeverity = ErrorSeverity.UNKNOWN  # Severidad clasificada

    def to_dict(self) -> Dict:
        """Serializa la entrada a dict (para JSON, reportes y la IA)."""
        return {
            # isoformat() porque datetime no es serializable a JSON directamente
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            # .value porque los Enum tampoco son serializables directamente
            'level': self.level.value,
            'correlation_id': self.correlation_id,
            'service': self.service,
            'class_name': self.class_name,
            # Se trunca a 500 chars para no saturar reportes ni el prompt de la IA
            'message': self.message[:500],
            'has_error_keyword': self.has_error_keyword,
            'error_type': self.error_type,
            'severity': self.severity.value if self.severity else None
        }