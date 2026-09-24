"""
Modelo de datos: conjunto de logs pertenecientes a una misma transacción.

El CorrelationAnalyzer agrupa los LogEntry por correlation-id y los empaqueta
en objetos CorrelationGroup. Cada grupo representa un flujo completo
(inicio → llamadas intermedias → fin o error), que es la unidad que se
analiza, filtra y envía a la IA.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from .log_entry import LogEntry


@dataclass
class CorrelationGroup:
    """Grupo de logs con el mismo correlation-id (= una transacción)."""
    correlation_id: str  # Id común que une todas las entradas del grupo
    entries: List[LogEntry] = field(default_factory=list)  # Logs ordenados del flujo
    start_time: Optional[datetime] = None  # Timestamp del primer log (inicio del flujo)
    end_time: Optional[datetime] = None    # Timestamp del último log (fin del flujo)
    has_success: bool = False   # True si hay algún mensaje de éxito en el grupo
    has_error: bool = False     # True si hay algún mensaje de error (dispara análisis)
    successful: bool = False    # True si el flujo terminó bien (sin errores)
    duration_seconds: Optional[float] = None  # end_time - start_time, calculado bajo demanda

    def get_errors(self) -> List[LogEntry]:
        """Retorna solo las entradas que tienen keyword de error."""
        return [e for e in self.entries if e.has_error_keyword]

    def get_success_indicators(self) -> List[str]:
        """
        Retorna mensajes que indican éxito de la transacción.

        Se buscan palabras de éxito en español e inglés porque los logs
        mezclan ambos idiomas según el microservicio que los emite.
        Se truncan a 200 chars para no saturar los reportes.
        """
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
        """
        Calcula la duración de la transacción en segundos.

        Solo es posible si hay timestamps de inicio y fin; en logs sin
        timestamp devuelve None. El resultado se guarda en el propio objeto
        para no recalcularlo en cada uso.
        """
        if self.start_time and self.end_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        return self.duration_seconds