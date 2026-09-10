"""
Parser de logs para extraer información estructurada.
"""
import re
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class LogParser:
    """Parser para logs de Kubernetes/Skooner."""
    
    def __init__(self):
        # Patrones para diferentes formatos de log
        self.patterns = {
            # Formato: 2024-01-15 10:30:45,123 ERROR [correlation-id] Mensaje
            'standard': re.compile(
                r'(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\s+'
                r'(?P<level>[A-Z]+)\s+'
                r'\[(?P<correlation_id>[^\]]+)\]\s+'
                r'(?P<message>.*)'
            ),
            # Formato: ERROR [2024-01-15 10:30:45,123] [correlation-id] Mensaje
            'bracket': re.compile(
                r'(?P<level>[A-Z]+)\s+'
                r'\[(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\]\s+'
                r'\[(?P<correlation_id>[^\]]+)\]\s+'
                r'(?P<message>.*)'
            ),
            # Formato simple: 2024-01-15 10:30:45 ERROR Mensaje
            'simple': re.compile(
                r'(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:,\d{3})?)\s+'
                r'(?P<level>[A-Z]+)\s+'
                r'(?P<message>.*)'
            ),
            # Formato JSON: {"timestamp": "...", "level": "...", "message": "..."}
            'json': re.compile(r'^\{.*\}$')
        }
        
        # Niveles de log por prioridad
        self.levels = {
            'TRACE': 0,
            'DEBUG': 1,
            'INFO': 2,
            'WARN': 3,
            'WARNING': 3,
            'ERROR': 4,
            'FATAL': 5,
            'CRITICAL': 5
        }
    
    def parse(self, content: str) -> List[Dict[str, Any]]:
        """
        Parsea el contenido del log y devuelve una lista de entradas.
        
        Args:
            content: Contenido del archivo de logs
            
        Returns:
            Lista de diccionarios con las entradas parseadas
        """
        if not content:
            logger.warning("Contenido vacío para parsear")
            return []
        
        lines = content.splitlines()
        parsed_entries = []
        
        # Intentar detectar formato principal
        format_detected = self._detect_format(lines[:10])
        logger.info(f"Formato detectado: {format_detected}")
        
        for i, line in enumerate(lines, 1):
            if not line.strip():
                continue
            
            try:
                entry = self._parse_line(line, format_detected)
                if entry:
                    # Agregar número de línea
                    entry['line_number'] = i
                    parsed_entries.append(entry)
            except Exception as e:
                logger.debug(f"Error parseando línea {i}: {str(e)}")
                # Si falla, intentar con formato simple
                entry = self._parse_line_simple(line)
                if entry:
                    entry['line_number'] = i
                    parsed_entries.append(entry)
        
        logger.info(f"✅ Parseados {len(parsed_entries)} logs de {len(lines)} líneas")
        return parsed_entries
    
    def _detect_format(self, sample_lines: List[str]) -> str:
        """Detecta el formato de log predominante."""
        formats_count = {fmt: 0 for fmt in self.patterns.keys()}
        
        for line in sample_lines:
            if not line.strip():
                continue
            
            for fmt, pattern in self.patterns.items():
                if fmt == 'json':
                    if line.strip().startswith('{'):
                        try:
                            json.loads(line)
                            formats_count['json'] += 1
                        except:
                            pass
                elif pattern.match(line):
                    formats_count[fmt] += 1
        
        # Devolver el formato con más coincidencias
        if formats_count:
            return max(formats_count, key=formats_count.get)
        return 'simple'
    
    def _parse_line(self, line: str, format_type: str) -> Optional[Dict[str, Any]]:
        """Parsea una línea individual según el formato detectado."""
        if format_type == 'json':
            return self._parse_json_line(line)
        
        pattern = self.patterns.get(format_type)
        if not pattern:
            return self._parse_line_simple(line)
        
        match = pattern.match(line)
        if not match:
            return self._parse_line_simple(line)
        
        data = match.groupdict()
        
        # Normalizar datos
        entry = {
            'timestamp': self._parse_timestamp(data.get('timestamp', '')),
            'level': data.get('level', 'INFO').upper(),
            'message': data.get('message', line).strip(),
            'correlation_id': data.get('correlation_id'),
            'raw': line
        }
        
        # Extraer información adicional
        entry.update(self._extract_metadata(entry['message']))
        
        return entry
    
    def _parse_line_simple(self, line: str) -> Optional[Dict[str, Any]]:
        """Parsea una línea con formato simple."""
        # Intentar con el patrón simple
        match = self.patterns['simple'].match(line)
        if match:
            data = match.groupdict()
            return {
                'timestamp': self._parse_timestamp(data.get('timestamp', '')),
                'level': data.get('level', 'INFO').upper(),
                'message': data.get('message', line).strip(),
                'correlation_id': None,
                'raw': line
            }
        
        # Si no coincide, devolver entrada básica
        return {
            'timestamp': None,
            'level': 'INFO',
            'message': line.strip(),
            'correlation_id': None,
            'raw': line
        }
    
    def _parse_json_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parsea una línea en formato JSON."""
        try:
            data = json.loads(line.strip())
            
            # Extraer campos comunes
            entry = {
                'timestamp': self._parse_timestamp(data.get('timestamp', '')),
                'level': str(data.get('level', data.get('severity', 'INFO'))).upper(),
                'message': data.get('message', data.get('msg', str(data))),
                'correlation_id': data.get('correlation_id', data.get('correlationId')),
                'raw': line,
                'metadata': data
            }
            
            return entry
        except json.JSONDecodeError:
            return None
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parsea un timestamp a objeto datetime."""
        if not timestamp_str:
            return None
        
        # Diferentes formatos de timestamp
        formats = [
            '%Y-%m-%d %H:%M:%S,%f',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%d/%b/%Y:%H:%M:%S %z',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def _extract_metadata(self, message: str) -> Dict[str, Any]:
        """Extrae metadatos adicionales del mensaje."""
        metadata = {}
        
        # Buscar errores de Kubernetes
        kubernetes_patterns = {
            'pod': re.compile(r'pod[=/]([^\s,]+)', re.IGNORECASE),
            'namespace': re.compile(r'namespace[=/]([^\s,]+)', re.IGNORECASE),
            'container': re.compile(r'container[=/]([^\s,]+)', re.IGNORECASE),
            'node': re.compile(r'node[=/]([^\s,]+)', re.IGNORECASE),
            'ip': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
            'port': re.compile(r':(\d+)'),
            'error_code': re.compile(r'error[= ]+(\w+)', re.IGNORECASE),
        }
        
        for key, pattern in kubernetes_patterns.items():
            match = pattern.search(message)
            if match:
                metadata[key] = match.group(1)
        
        # Detectar si es un error
        error_keywords = ['error', 'fail', 'exception', 'timeout', 'refused', 'connection']
        if any(keyword in message.lower() for keyword in error_keywords):
            metadata['is_error_likely'] = True
        
        return metadata
    
    def filter_by_level(self, entries: List[Dict[str, Any]], level: str) -> List[Dict[str, Any]]:
        """Filtra entradas por nivel de log."""
        level_priority = self.levels.get(level.upper(), 2)
        return [
            entry for entry in entries
            if self.levels.get(entry.get('level', 'INFO'), 2) >= level_priority
        ]
    
    def filter_errors(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filtra solo entradas de error."""
        return self.filter_by_level(entries, 'ERROR')
    
    def get_correlation_id(self, entry: Dict[str, Any]) -> Optional[str]:
        """Obtiene el correlation ID de una entrada."""
        return entry.get('correlation_id')
    
    def group_by_correlation(self, entries: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Agrupa entradas por correlation ID."""
        groups = {}
        for entry in entries:
            corr_id = self.get_correlation_id(entry)
            if corr_id:
                if corr_id not in groups:
                    groups[corr_id] = []
                groups[corr_id].append(entry)
        return groups