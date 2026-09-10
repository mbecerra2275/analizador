"""
Generador de reportes en formato Markdown.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

class MarkdownReporter:
    """Genera reportes en formato Markdown."""
    
    def __init__(self, output_dir: str = "output/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, data: Dict[str, Any]) -> str:
        """
        Genera un reporte Markdown.
        
        Args:
            data: Datos del análisis
            
        Returns:
            Ruta del archivo generado
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"analysis_report_{timestamp}.md"
        
        content = self._build_markdown(data)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(filename)
    
    def _build_markdown(self, data: Dict[str, Any]) -> str:
        """Construye el contenido del reporte en Markdown."""
        lines = []
        
        # Título
        lines.append("# 📊 Reporte de Análisis de Logs")
        lines.append("")
        lines.append(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Archivo:** `{data.get('file', 'N/A')}`")
        lines.append("")
        
        # Resumen
        lines.append("## 📈 Resumen")
        lines.append("")
        summary = data.get('summary', {})
        lines.append(f"- 📊 **Total de logs:** {summary.get('total_logs', 0):,}")
        lines.append(f"- 🔗 **Transacciones:** {summary.get('total_groups', 0):,}")
        lines.append(f"- ✅ **Grupos filtrados:** {summary.get('filtered_groups', 0):,}")
        lines.append(f"- ⚠️ **Errores detectados:** {summary.get('total_errors', 0):,}")
        lines.append("")
        
        # Niveles de log
        levels = summary.get('levels', {})
        if levels:
            lines.append("### 📊 Niveles de Log")
            lines.append("")
            for level, count in sorted(levels.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"- **{level}:** {count:,}")
            lines.append("")
        
        # Análisis IA
        ai_analysis = data.get('ai_analysis', {})
        lines.append("## 🤖 Análisis con IA")
        lines.append("")
        lines.append(f"**Estado:** {ai_analysis.get('status', 'No disponible')}")
        lines.append("")
        
        if ai_analysis.get('status') == 'success':
            analysis = ai_analysis.get('analysis', '')
            if analysis:
                lines.append(analysis)
                lines.append("")
        else:
            lines.append("⚠️ Análisis IA no disponible. Revisar que Ollama esté corriendo.")
            lines.append("")
        
        # Errores
        errors = data.get('errors', [])
        if errors:
            lines.append("## ⚠️ Errores Encontrados")
            lines.append("")
            
            for i, error in enumerate(errors[:20], 1):
                lines.append(f"### {i}. Correlation ID: `{error.get('correlation_id', 'N/A')}`")
                lines.append("")
                lines.append(f"- **Cantidad de errores:** {error.get('error_count', 0)}")
                lines.append(f"- **Timestamp:** {error.get('timestamp', 'N/A')}")
                lines.append("")
                
                messages = error.get('messages', [])
                if messages:
                    lines.append("**Mensajes de error:**")
                    lines.append("")
                    for msg in messages[:5]:
                        lines.append(f"```")
                        lines.append(msg)
                        lines.append(f"```")
                        lines.append("")
                    
                    if len(messages) > 5:
                        lines.append(f"... y {len(messages) - 5} mensajes más")
                        lines.append("")
            
            if len(errors) > 20:
                lines.append(f"... y {len(errors) - 20} errores más")
                lines.append("")
        else:
            lines.append("## ✅ No se encontraron errores")
            lines.append("")
            lines.append("¡Todo parece funcionar correctamente!")
            lines.append("")
        
        # Recomendaciones
        recommendations = data.get('recommendations', [])
        if recommendations:
            lines.append("## 💡 Recomendaciones")
            lines.append("")
            for rec in recommendations:
                lines.append(f"- {rec}")
            lines.append("")
        
        # Pie de página
        lines.append("---")
        lines.append("")
        lines.append("_Reporte generado automáticamente por el Analizador de Logs con IA_")
        
        return "\n".join(lines)