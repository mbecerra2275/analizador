# app/reporters/markdown_reporter.py
import os
from datetime import datetime
from typing import Dict, List

class MarkdownReporter:
    def __init__(self, output_dir: str = "output/reports/"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_report(self, data: Dict) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_report_{timestamp}.md"
        filepath = os.path.join(self.output_dir, filename)
        
        content = self._build_content(data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def _build_content(self, data: Dict) -> str:
        lines = []
        lines.append("# 📊 Análisis de Logs - Reporte")
        lines.append("")
        lines.append(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        stats = data.get('statistics', {})
        lines.append("## 📈 Resumen")
        lines.append("")
        lines.append(f"- **Total Transacciones:** {stats.get('total_transactions', 0)}")
        lines.append(f"- **Tasa de Éxito:** {stats.get('success_rate', 0):.1f}%")
        lines.append(f"- **Errores Reales (únicos):** {data.get('total_errors_found', 0)}")
        lines.append(f"- **Falsos Positivos:** {data.get('total_false_positives', 0)}")
        lines.append("")
        
        # Severidad
        if data.get('severity_summary'):
            lines.append("### Severidad de Errores")
            lines.append("")
            for severity, count in data.get('severity_summary', {}).items():
                emoji = self._get_severity_emoji(severity)
                lines.append(f"- {emoji} **{severity}**: {count}")
            lines.append("")
        
        # Tipos de error
        if data.get('error_types_summary'):
            lines.append("### Tipos de Error")
            lines.append("")
            for error_type, count in data.get('error_types_summary', {}).items():
                lines.append(f"- **{error_type}**: {count}")
            lines.append("")
        
        # Análisis de IA
        if data.get('ai_analysis'):
            lines.append("## 🤖 Análisis de IA")
            lines.append("")
            lines.append(data['ai_analysis'])
            lines.append("")
        
        # Errores Reales
        if data.get('true_errors'):
            lines.append("## 🔴 Errores Reales Detectados")
            lines.append("")
            lines.append(f"Mostrando {len(data['true_errors'])} de {data.get('total_errors_found', 0)} errores únicos")
            lines.append("")
            
            for i, error in enumerate(data['true_errors'][:15], 1):
                entry = error['entry']
                severity = error.get('severity', 'UNKNOWN')
                emoji = self._get_severity_emoji(str(severity))
                
                lines.append(f"### {emoji} Error {i}: {error.get('type', 'UNKNOWN')}")
                lines.append("")
                lines.append(f"- **Severidad:** `{severity}`")
                lines.append(f"- **Servicio:** `{entry.service}`")
                lines.append(f"- **Correlation ID:** `{entry.correlation_id or 'N/A'}`")
                if entry.timestamp:
                    lines.append(f"- **Timestamp:** `{entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}`")
                lines.append("")
                lines.append("**Mensaje:**")
                lines.append("```")
                lines.append(entry.message[:300])
                lines.append("```")
                lines.append("")
                if entry.stack_trace:
                    lines.append("**Stack Trace:**")
                    lines.append("```")
                    lines.append(entry.stack_trace[:200])
                    lines.append("```")
                    lines.append("")
                lines.append("---")
                lines.append("")
        
        # Recomendaciones
        if data.get('recommendations'):
            lines.append("## 💡 Recomendaciones")
            lines.append("")
            for i, rec in enumerate(data['recommendations'], 1):
                lines.append(f"{i}. {rec}")
            lines.append("")
        
        return '\n'.join(lines)
    
    def _get_severity_emoji(self, severity: str) -> str:
        emojis = {
            'CRITICAL': '🚨',
            'HIGH': '🔴',
            'MEDIUM': '🟡',
            'LOW': '🟢',
            'INFO': 'ℹ️',
            'UNKNOWN': '❓'
        }
        return emojis.get(severity.upper(), '❓')