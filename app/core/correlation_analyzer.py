"""
Analizador de correlaciones para agrupar logs por correlation ID.
"""
import re
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CorrelationAnalyzer:
    """Analiza y agrupa logs por correlation ID."""
    
    def __init__(self):
        # Patrón para encontrar correlation IDs
        self.correlation_patterns = [
            re.compile(r'correlation[_-]?id[=:]\s*([a-zA-Z0-9\-_]+)', re.IGNORECASE),
            re.compile(r'\[([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\]'),
            re.compile(r'transaction[_-]?id[=:]\s*([a-zA-Z0-9\-_]+)', re.IGNORECASE),
            re.compile(r'request[_-]?id[=:]\s*([a-zA-Z0-9\-_]+)', re.IGNORECASE),
            re.compile(r'trace[_-]?id[=:]\s*([a-zA-Z0-9\-_]+)', re.IGNORECASE),
            re.compile(r'span[_-]?id[=:]\s*([a-zA-Z0-9\-_]+)', re.IGNORECASE),
        ]
        
        # Patrón para extraer timestamp
        self.timestamp_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:,\d{3})?(?:Z|[+-]\d{2}:?\d{2})?)'
        )
    
    def group_by_correlation(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Agrupa entradas de log por correlation ID.
        
        Args:
            entries: Lista de entradas de log parseadas
            
        Returns:
            Lista de grupos con sus entradas asociadas
        """
        if not entries:
            return []
        
        # Agrupar por correlation ID
        groups = defaultdict(list)
        entries_without_correlation = []
        
        for entry in entries:
            # Intentar obtener correlation_id de varias fuentes
            corr_id = self._extract_correlation_id(entry)
            
            if corr_id:
                groups[corr_id].append(entry)
            else:
                entries_without_correlation.append(entry)
        
        # Si hay entradas sin correlation ID, agruparlas por timestamp cercano
        if entries_without_correlation:
            time_groups = self._group_by_time(entries_without_correlation)
            for time_id, group_entries in time_groups.items():
                groups[time_id] = group_entries
        
        # Convertir a lista de grupos
        result = []
        for corr_id, entries_list in groups.items():
            group = {
                'correlation_id': corr_id,
                'entries': entries_list,
                'count': len(entries_list),
                'has_errors': self._has_errors(entries_list),
                'error_count': self._count_errors(entries_list),
                'timestamp': self._get_first_timestamp(entries_list),
                'levels': self._get_levels(entries_list),
                'error_messages': self._get_error_messages(entries_list)
            }
            result.append(group)
        
        # Ordenar por timestamp - MANEJO DE None
        def get_sort_key(group):
            """Obtiene la clave de ordenación manejando None."""
            ts = group.get('timestamp')
            if ts is None:
                return ''  # Los None van al final
            return ts
        
        result.sort(key=get_sort_key)
        
        logger.info(f"✅ Agrupados {len(entries)} logs en {len(result)} grupos")
        return result
    
    def _extract_correlation_id(self, entry: Dict[str, Any]) -> Optional[str]:
        """Extrae el correlation ID de una entrada."""
        # Primero verificar si ya existe en la entrada
        if 'correlation_id' in entry and entry['correlation_id']:
            return str(entry['correlation_id'])
        
        # Buscar en el mensaje
        message = entry.get('message', '')
        if not message:
            return None
        
        # Intentar cada patrón
        for pattern in self.correlation_patterns:
            match = pattern.search(message)
            if match:
                return match.group(1)
        
        # Buscar en metadata
        if 'metadata' in entry and isinstance(entry['metadata'], dict):
            metadata = entry['metadata']
            for key in ['correlation_id', 'correlationId', 'transaction_id', 'trace_id', 'span_id']:
                if key in metadata and metadata[key]:
                    return str(metadata[key])
        
        return None
    
    def _group_by_time(self, entries: List[Dict[str, Any]], time_window: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Agrupa entradas por proximidad temporal.
        
        Args:
            entries: Lista de entradas sin correlation ID
            time_window: Ventana de tiempo en segundos para agrupar
            
        Returns:
            Diccionario de grupos por timestamp
        """
        groups = defaultdict(list)
        
        for entry in entries:
            timestamp = self._parse_timestamp(entry.get('timestamp'))
            if timestamp:
                # Redondear al minuto más cercano para agrupar
                rounded = timestamp.replace(second=0, microsecond=0)
                key = rounded.isoformat()
            else:
                # Si no hay timestamp, usar un hash del mensaje
                key = f"no_ts_{hash(entry.get('message', '')) % 10000}"
            
            groups[key].append(entry)
        
        # Si hay muchos grupos pequeños, fusionarlos
        final_groups = {}
        sorted_keys = sorted(groups.keys())
        
        i = 0
        while i < len(sorted_keys):
            key = sorted_keys[i]
            if len(groups[key]) < 3 and i + 1 < len(sorted_keys):
                # Fusionar con el siguiente grupo
                next_key = sorted_keys[i + 1]
                if len(groups[next_key]) < 5:
                    merged_key = f"merged_{i}"
                    final_groups[merged_key] = groups[key] + groups[next_key]
                    i += 2
                    continue
            
            final_groups[key] = groups[key]
            i += 1
        
        return final_groups
    
    def _parse_timestamp(self, timestamp_str: Any) -> Optional[datetime]:
        """Parsea un timestamp a objeto datetime."""
        if not timestamp_str:
            return None
        
        if isinstance(timestamp_str, datetime):
            return timestamp_str
        
        if isinstance(timestamp_str, str):
            formats = [
                '%Y-%m-%d %H:%M:%S,%f',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S',
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt)
                except ValueError:
                    continue
        
        return None
    
    def _has_errors(self, entries: List[Dict[str, Any]]) -> bool:
        """Verifica si el grupo contiene errores."""
        return any(self._is_error(entry) for entry in entries)
    
    def _count_errors(self, entries: List[Dict[str, Any]]) -> int:
        """Cuenta el número de errores en el grupo."""
        return sum(1 for entry in entries if self._is_error(entry))
    
    def _is_error(self, entry: Dict[str, Any]) -> bool:
        """Verifica si una entrada es un error."""
        level = str(entry.get('level', '')).upper()
        if level in ['ERROR', 'FATAL', 'CRITICAL']:
            return True
        
        message = str(entry.get('message', '')).lower()
        error_keywords = ['error', 'exception', 'failed', 'failure', 'timeout', 'refused']
        return any(keyword in message for keyword in error_keywords)
    
    def _get_first_timestamp(self, entries: List[Dict[str, Any]]) -> Optional[str]:
        """Obtiene el timestamp más antiguo del grupo."""
        timestamps = []
        for entry in entries:
            ts = entry.get('timestamp')
            if ts:
                if isinstance(ts, datetime):
                    timestamps.append(ts)
                elif isinstance(ts, str):
                    parsed = self._parse_timestamp(ts)
                    if parsed:
                        timestamps.append(parsed)
        
        if timestamps:
            return min(timestamps).isoformat()
        return None
    
    def _get_levels(self, entries: List[Dict[str, Any]]) -> List[str]:
        """Obtiene los niveles de log presentes en el grupo."""
        levels = set()
        for entry in entries:
            level = str(entry.get('level', 'INFO')).upper()
            levels.add(level)
        return sorted(levels)
    
    def _get_error_messages(self, entries: List[Dict[str, Any]]) -> List[str]:
        """Obtiene los mensajes de error del grupo."""
        messages = []
        for entry in entries:
            if self._is_error(entry):
                message = str(entry.get('message', ''))
                if message:
                    messages.append(message)
        return messages
    
    def find_related_groups(self, groups: List[Dict[str, Any]], max_delta: int = 60) -> List[List[Dict[str, Any]]]:
        """
        Encuentra grupos relacionados por proximidad temporal.
        
        Args:
            groups: Lista de grupos
            max_delta: Diferencia máxima en segundos
            
        Returns:
            Lista de grupos relacionados
        """
        if len(groups) < 2:
            return [groups]
        
        # Ordenar por timestamp - MANEJO DE None
        def get_sort_key(group):
            ts = group.get('timestamp')
            if ts is None:
                return ''
            return ts
        
        sorted_groups = sorted(groups, key=get_sort_key)
        
        related = []
        current_group = [sorted_groups[0]]
        
        for i in range(1, len(sorted_groups)):
            prev_ts = self._parse_timestamp(sorted_groups[i-1].get('timestamp'))
            curr_ts = self._parse_timestamp(sorted_groups[i].get('timestamp'))
            
            if prev_ts and curr_ts:
                delta = (curr_ts - prev_ts).total_seconds()
                if delta <= max_delta:
                    current_group.append(sorted_groups[i])
                else:
                    related.append(current_group)
                    current_group = [sorted_groups[i]]
            else:
                current_group.append(sorted_groups[i])
        
        if current_group:
            related.append(current_group)
        
        return related
    
    def get_correlation_summary(self, groups: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera un resumen de los grupos de correlación.
        
        Returns:
            Diccionario con estadísticas de los grupos
        """
        if not groups:
            return {
                'total_groups': 0,
                'total_entries': 0,
                'groups_with_errors': 0,
                'total_errors': 0,
                'avg_group_size': 0,
                'max_group_size': 0
            }
        
        total_entries = sum(g['count'] for g in groups)
        groups_with_errors = sum(1 for g in groups if g['has_errors'])
        total_errors = sum(g['error_count'] for g in groups)
        avg_size = total_entries / len(groups)
        max_size = max(g['count'] for g in groups)
        
        return {
            'total_groups': len(groups),
            'total_entries': total_entries,
            'groups_with_errors': groups_with_errors,
            'total_errors': total_errors,
            'avg_group_size': round(avg_size, 2),
            'max_group_size': max_size
        }