# app/core/correlation_analyzer.py
from datetime import datetime
from typing import Dict, List

class CorrelationGroup:
    def __init__(self, correlation_id, entries=None):
        self.correlation_id = correlation_id
        self.entries = entries or []
        self.start_time = None
        self.end_time = None
        self.has_success = False
        self.has_error = False
        self.successful = False
        self.duration_seconds = None
        
        if self.entries:
            self.start_time = self.entries[0].timestamp if self.entries else None
            self.end_time = self.entries[-1].timestamp if self.entries else None
            self.has_success = any('exito' in e.message.lower() or 
                                  'respondió correctamente' in e.message.lower() 
                                  for e in self.entries)
            self.has_error = any(e.has_error_keyword for e in self.entries)
            self.successful = self.has_success or (not self.has_error and len(self.entries) > 2)
            
            if self.start_time and self.end_time:
                self.duration_seconds = (self.end_time - self.start_time).total_seconds()
    
    def get_errors(self):
        return [e for e in self.entries if e.has_error_keyword]

class CorrelationAnalyzer:
    def __init__(self, entries: List[LogEntry]):
        self.entries = entries
        self.groups: Dict[str, CorrelationGroup] = {}
        
    def analyze(self) -> Dict[str, CorrelationGroup]:
        groups = {}
        
        for entry in self.entries:
            if entry.correlation_id:
                if entry.correlation_id not in groups:
                    groups[entry.correlation_id] = []
                groups[entry.correlation_id].append(entry)
        
        for corr_id, entries in groups.items():
            entries.sort(key=lambda x: x.timestamp if x.timestamp else datetime.min)
            self.groups[corr_id] = CorrelationGroup(corr_id, entries)
        
        return self.groups
    
    def get_statistics(self) -> Dict:
        total = len(self.groups)
        successful = sum(1 for g in self.groups.values() if g.successful)
        failed = total - successful
        
        durations = [g.duration_seconds for g in self.groups.values() if g.duration_seconds]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            'total_transactions': total,
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'avg_duration': avg_duration
        }