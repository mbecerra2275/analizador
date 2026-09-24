"""
Filtro inteligente para eliminar falsos positivos.

Los logs de Kubernetes están llenos de ruido operativo (health checks,
probes, métricas de Prometheus...) que el parser marca como "error" por
contener palabras como "probe failed" o "error" en otro sentido. Si ese
ruido llegara a la IA, gastaría tokens y contaminaría el diagnóstico.
Este filtro se aplica DESPUÉS de correlacionar y ANTES de enviar a la IA.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SmartFilter:
    """Descarta grupos y entradas irrelevantes antes del análisis IA."""

    def __init__(self):
        # Patrones de ruido operativo típico de Kubernetes/observabilidad.
        # Se comparan en minúsculas con `in` (subcadena), así que deben ser
        # frases distintivas para no filtrar errores reales por accidente.
        self.false_positive_patterns = [
            'health check',
            'heartbeat',
            'keepalive',
            'liveness probe',
            'readiness probe',
            'startup probe',
            'metrics collection',
            'log rotation',
            'garbage collection',
            'scraping metrics',
            'prometheus',
            'grafana',
            'jaeger',
            'fluentd',
            'filebeat',
            'elasticsearch'
        ]
    
    def filter_groups(self, groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filtra grupos de correlación, quedándose solo con los relevantes.

        Args:
            groups: Lista de grupos (salida de CorrelationAnalyzer).

        Returns:
            Sublista con los grupos relevantes. Registra en el log cuántos
            se descartaron para auditar la agresividad del filtro.
        """
        if not groups:
            return []

        filtered = []
        for group in groups:
            # Cada grupo se evalúa por separado con las reglas de _is_relevant.
            if self._is_relevant(group):
                filtered.append(group)

        logger.info(f"✅ Filtrados {len(groups) - len(filtered)} grupos irrelevantes")
        return filtered
    
    def _is_relevant(self, group: Dict[str, Any]) -> bool:
        """
        Decide si un grupo merece llegar al análisis IA.

        Reglas en orden (la primera que aplique decide):
        1. Con errores → siempre relevante (el filtro de ruido no debe
           ocultar errores reales).
        2. Grupo grande (>10 logs) → relevante por volumen anómalo aunque
           no tenga errores explícitos.
        3. Con mensajes de error → relevante salvo que TODOS sean ruido
           conocido (ej: un probe que loguea "error" de forma rutinaria).
        4. Resto → relevante si al menos un mensaje NO es ruido; si todo
           es ruido (o no hay mensajes), se descarta.

        Args:
            group: Grupo de logs con claves has_errors, count,
                error_messages y entries.

        Returns:
            True si el grupo es relevante, False si es descartable.
        """
        # Regla 1: cualquier error explícito pasa el filtro.
        if group.get('has_errors', False):
            return True

        # Regla 2: un grupo muy grande es sospechoso por sí mismo
        # (bucles de reintento, tormentas de logs...).
        if group.get('count', 0) > 10:
            return True

        # Regla 3: si hay mensajes de error, solo se descarta el grupo
        # cuando alguno coincide con ruido conocido.
        error_messages = group.get('error_messages', [])
        if error_messages:
            for msg in error_messages:
                if self._is_false_positive(msg):
                    return False
            return True

        # Regla 4: basta un mensaje no-ruido para conservar el grupo.
        entries = group.get('entries', [])
        for entry in entries:
            message = entry.get('message', '')
            if message and not self._is_false_positive(message):
                return True

        return False
    
    def _is_false_positive(self, message: str) -> bool:
        """
        Verifica si un mensaje es ruido operativo conocido.

        Comparación case-insensitive por subcadena: basta que el mensaje
        contenga p.ej. "liveness probe" para marcarse como falso positivo.

        Args:
            message: Mensaje a verificar.

        Returns:
            True si coincide con algún patrón de ruido, False si no.
        """
        message_lower = message.lower()
        for pattern in self.false_positive_patterns:
            if pattern in message_lower:
                return True
        return False
    
    def filter_entries(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filtra entradas individuales (nivel log, no grupo).

        Se usa cuando se quiere limpiar una lista plana de logs en vez de
        grupos correlacionados. Criterio: los niveles ERROR/FATAL/CRITICAL
        siempre se conservan; el resto solo si no son ruido conocido.

        Args:
            entries: Lista de entradas de log parseadas.

        Returns:
            Sublista con las entradas conservadas.
        """
        if not entries:
            return []

        filtered = []
        for entry in entries:
            message = entry.get('message', '')
            level = entry.get('level', '').upper()

            # Los niveles graves nunca se filtran, sean ruido o no.
            if level in ['ERROR', 'FATAL', 'CRITICAL']:
                filtered.append(entry)
                continue

            # Niveles informativos: solo pasan si no son ruido.
            if message and not self._is_false_positive(message):
                filtered.append(entry)

        return filtered