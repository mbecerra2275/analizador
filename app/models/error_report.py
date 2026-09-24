"""
Modelo de datos: resultado agregado de un análisis completo.

Es el contenedor final que resume todo el pipeline (parseo → correlación →
filtrado → IA) en cifras y listas listas para pintar en el reporte HTML
o mostrar en la GUI. Separa errores reales de falsos positivos para que
las métricas no se inflen con ruido (health checks, métricas, etc.).
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional


@dataclass
class ErrorReport:
    """Reporte final de análisis de un archivo de logs."""
    total_transactions: int = 0  # Nº total de grupos/transacciones analizadas
    total_errors: int = 0        # Nº total de errores reales hallados
    true_errors: List[Dict] = field(default_factory=list)       # Errores confirmados (van al reporte)
    false_positives: List[Dict] = field(default_factory=list)   # Ruido descartado (solo para auditoría)
    severity_summary: Dict[str, int] = field(default_factory=dict)    # Conteo por severidad: {"critical": 2, ...}
    error_types_summary: Dict[str, int] = field(default_factory=dict)  # Conteo por tipo: {"timeout": 5, ...}
    affected_services: List[str] = field(default_factory=list)  # Microservicios con al menos un error
    analysis_timestamp: datetime = field(default_factory=datetime.now)  # Cuándo se hizo el análisis
    ai_analysis: Optional[str] = None              # Texto del diagnóstico generado por Ollama
    recommendations: List[str] = field(default_factory=list)  # Acciones sugeridas (de la IA o de reglas)
    statistics: Dict[str, any] = field(default_factory=dict)  # Métricas extra libres (duraciones, ratios...)