# app/models/correlation_group.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from .log_entry import LogEntry

@dataclass
class CorrelationGroup:
    """Grupo de logs con el mismo correlation-id"""
    correlation_id: str
    entries: List[LogEntry] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    has_success: bool = False
    has_error: bool = False
    successful: bool = False
    duration_seconds: Optional[float] = None
    
    def get_errors(self) -> List[LogEntry]:
        """Retorna solo las entradas que tienen keyword de error"""
        return [e for e in self.entries if e.has_error_keyword]
    
    def get_success_indicators(self) -> List[str]:
        """Retorna mensajes que indican éxito de la transacción"""
        indicators = []
        for entry in self.entries:
            msg_lower = entry.message.lower()
            if 'exito' in msg_lower:
                indicators.append(entry.message[:200])
            elif 'respondió correctamente' in msg_lower:
                indicators.append(entry.message[:200])
            elif 'success' in msg_lower:
                indicators.append(entry.message[:200])
        return indicators
    
    def calculate_duration(self) -> Optional[float]:
        """Calcula la duración de la transacción en segundos"""
        if self.start_time and self.end_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        return self.duration_seconds