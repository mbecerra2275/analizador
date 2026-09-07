# app/core/log_parser.py
import re
from datetime import datetime
from typing import List, Optional

class LogEntry:
    def __init__(self, timestamp=None, level="INFO", correlation_id=None, 
                 service="unknown", class_name="Unknown", message="", 
                 raw_line="", has_error_keyword=False, stack_trace=None):
        self.timestamp = timestamp
        self.level = level
        self.correlation_id = correlation_id
        self.service = service
        self.class_name = class_name
        self.message = message[:500]
        self.raw_line = raw_line[:1000]
        self.has_error_keyword = has_error_keyword
        self.stack_trace = stack_trace

class LogParser:
    TIMESTAMP_PATTERN = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})'
    CORRELATION_PATTERN = r'ssff-correlation-id=([a-f0-9]+)'
    LEVEL_PATTERN = r'(INFO|WARN|ERROR|DEBUG|TRACE)'
    CLASS_PATTERN = r'\[([a-zA-Z0-9\.]+)\]'
    SERVICE_PATTERN = r'\[EVENT (SUCCESS|FAILURE) -> /([a-zA-Z0-9\-\.]+)/'
    
    def __init__(self, log_lines: List[str]):
        self.log_lines = log_lines
        self.parsed_entries = []
        
    def parse_all(self) -> List[LogEntry]:
        self.parsed_entries = []
        for line in self.log_lines:
            if not line.strip():
                continue
            entry = self.parse_line(line)
            if entry:
                self.parsed_entries.append(entry)
        return self.parsed_entries
    
    def parse_line(self, line: str) -> Optional[LogEntry]:
        timestamp = None
        timestamp_match = re.search(self.TIMESTAMP_PATTERN, line)
        if timestamp_match:
            try:
                timestamp = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S,%f')
            except:
                pass
        
        corr_match = re.search(self.CORRELATION_PATTERN, line)
        correlation_id = corr_match.group(1) if corr_match else None
        
        level_match = re.search(self.LEVEL_PATTERN, line)
        level = level_match.group(1) if level_match else "INFO"
        
        class_match = re.search(self.CLASS_PATTERN, line)
        class_name = class_match.group(1) if class_match else "Unknown"
        
        service_match = re.search(self.SERVICE_PATTERN, line)
        service = service_match.group(2) if service_match else "unknown-service"
        
        has_error_keyword = 'ERROR' in line or 'FAILURE' in line or 'Exception' in line
        
        # Extraer mensaje simple
        parts = re.split(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.*?(?:INFO|WARN|ERROR|DEBUG|TRACE)', line)
        message = parts[1].strip() if len(parts) > 1 else line.strip()
        message = re.sub(r'\x1b\[[0-9;]*m', '', message)[:500]
        
        stack_trace = None
        if 'at ' in line and ('Exception' in line or 'Error' in line):
            stack_trace = line.strip()
        
        return LogEntry(
            timestamp=timestamp,
            level=level,
            correlation_id=correlation_id,
            service=service,
            class_name=class_name,
            message=message,
            raw_line=line,
            has_error_keyword=has_error_keyword,
            stack_trace=stack_trace
        )