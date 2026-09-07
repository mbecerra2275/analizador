# app/models/log_entry.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum

class LogLevel(Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    DEBUG = "DEBUG"
    TRACE = "TRACE"

class ErrorSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    UNKNOWN = "unknown"

@dataclass
class LogEntry:
    """Representa una línea de log parseada"""
    timestamp: Optional[datetime]
    level: LogLevel
    correlation_id: Optional[str]
    service: str
    class_name: str
    message: str
    raw_line: str
    has_error_keyword: bool
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None
    severity: ErrorSeverity = ErrorSeverity.UNKNOWN
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'level': self.level.value,
            'correlation_id': self.correlation_id,
            'service': self.service,
            'class_name': self.class_name,
            'message': self.message[:500],
            'has_error_keyword': self.has_error_keyword,
            'error_type': self.error_type,
            'severity': self.severity.value if self.severity else None
        }