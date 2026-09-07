# app/models/error_report.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional

@dataclass
class ErrorReport:
    """Reporte final de análisis"""
    total_transactions: int = 0
    total_errors: int = 0
    true_errors: List[Dict] = field(default_factory=list)
    false_positives: List[Dict] = field(default_factory=list)
    severity_summary: Dict[str, int] = field(default_factory=dict)
    error_types_summary: Dict[str, int] = field(default_factory=dict)
    affected_services: List[str] = field(default_factory=list)
    analysis_timestamp: datetime = field(default_factory=datetime.now)
    ai_analysis: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)
    statistics: Dict[str, any] = field(default_factory=dict)