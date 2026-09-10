"""
Filtro inteligente para eliminar falsos positivos.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class SmartFilter:
    """Filtra logs para eliminar falsos positivos."""
    
    def __init__(self):
        # Palabras clave de falsos positivos comunes
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
        Filtra grupos para eliminar falsos positivos.
        
        Args:
            groups: Lista de grupos de logs
            
        Returns:
            Lista de grupos filtrados
        """
        if not groups:
            return []
        
        filtered = []
        for group in groups:
            # Verificar si el grupo es relevante
            if self._is_relevant(group):
                filtered.append(group)
        
        logger.info(f"✅ Filtrados {len(groups) - len(filtered)} grupos irrelevantes")
        return filtered
    
    def _is_relevant(self, group: Dict[str, Any]) -> bool:
        """
        Determina si un grupo es relevante.
        
        Args:
            group: Grupo de logs
            
        Returns:
            True si el grupo es relevante, False en caso contrario
        """
        # Si tiene errores, es relevante
        if group.get('has_errors', False):
            return True
        
        # Si tiene muchos logs, es relevante
        if group.get('count', 0) > 10:
            return True
        
        # Verificar mensajes de error
        error_messages = group.get('error_messages', [])
        if error_messages:
            # Verificar si son falsos positivos
            for msg in error_messages:
                if self._is_false_positive(msg):
                    return False
            return True
        
        # Verificar mensajes regulares
        entries = group.get('entries', [])
        for entry in entries:
            message = entry.get('message', '')
            if message and not self._is_false_positive(message):
                # Si hay algún mensaje que no es falso positivo, mantenerlo
                return True
        
        return False
    
    def _is_false_positive(self, message: str) -> bool:
        """
        Verifica si un mensaje es un falso positivo.
        
        Args:
            message: Mensaje a verificar
            
        Returns:
            True si es falso positivo, False en caso contrario
        """
        message_lower = message.lower()
        for pattern in self.false_positive_patterns:
            if pattern in message_lower:
                return True
        return False
    
    def filter_entries(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filtra entradas individuales.
        
        Args:
            entries: Lista de entradas de log
            
        Returns:
            Lista de entradas filtradas
        """
        if not entries:
            return []
        
        filtered = []
        for entry in entries:
            message = entry.get('message', '')
            level = entry.get('level', '').upper()
            
            # Mantener errores
            if level in ['ERROR', 'FATAL', 'CRITICAL']:
                filtered.append(entry)
                continue
            
            # Mantener si no es falso positivo
            if message and not self._is_false_positive(message):
                filtered.append(entry)
        
        return filtered