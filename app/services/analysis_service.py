# app/services/analysis_service.py
import os
from typing import Dict, List, Optional
from datetime import datetime

from ..core.log_parser import LogParser
from ..core.correlation_analyzer import CorrelationAnalyzer
from ..core.smart_filter import SmartFilter
from ..reporters.markdown_reporter import MarkdownReporter
from ..ai.ollama_client import OllamaClient

class AnalysisService:
    def __init__(self, config: Dict):
        self.config = config
        self.reporter = MarkdownReporter(config.get('output_dir', 'output/reports/'))
        self.verbose = config.get('verbose', False)
        
        # Inicializar Ollama
        self.ai_available = False
        try:
            self.ollama = OllamaClient(
                model=config.get('ai_model', 'qwen2.5-coder:1.5b'),
                temperature=config.get('temperature', 0.3)
            )
            self.ai_available = self.ollama.available
        except Exception as e:
            print(f"⚠️  AI no disponible: {e}")
    
    def _log(self, message: str):
        if self.verbose:
            print(f"  {message}")
    
    def analyze_log_file(self, log_file: str, use_ai: bool = True) -> Dict:
        print(f"📂 Analizando archivo: {os.path.basename(log_file)}")
        
        # 1. Cargar y parsear logs
        self._log("Cargando y parseando logs...")
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        parser = LogParser(lines)
        entries = parser.parse_all()
        print(f"   ✅ Parseadas {len(entries)} líneas de log")
        
        # 2. Agrupar por correlation-id
        self._log("Agrupando por correlation-id...")
        analyzer = CorrelationAnalyzer(entries)
        groups = analyzer.analyze()
        stats = analyzer.get_statistics()
        print(f"   ✅ Agrupadas {len(groups)} transacciones")
        
        # 3. Filtrar falsos positivos y duplicados
        self._log("Clasificando errores...")
        true_errors = []
        false_positives = []
        severity_summary = {}
        error_types_summary = {}
        affected_services = set()
        seen_errors = set()  # Para evitar duplicados
        
        for group in groups.values():
            true_err, false_pos = SmartFilter.classify(group)
            
            for error in true_err:
                # Evitar duplicados exactos
                msg_key = error['entry'].message[:150].strip()
                if msg_key in seen_errors:
                    continue
                seen_errors.add(msg_key)
                
                true_errors.append(error)
                severity = str(error.get('severity', 'UNKNOWN')).upper()
                severity_summary[severity] = severity_summary.get(severity, 0) + 1
                
                error_type = error.get('type', 'UNKNOWN')
                error_types_summary[error_type] = error_types_summary.get(error_type, 0) + 1
                
                if error['entry'].service:
                    affected_services.add(error['entry'].service)
            
            false_positives.extend(false_pos)
        
        print(f"   ✅ Errores reales únicos: {len(true_errors)}")
        print(f"   ✅ Falsos positivos: {len(false_positives)}")
        
        # 4. Análisis con IA
        ai_analysis = None
        recommendations = []
        
        if use_ai and self.ai_available and true_errors:
            print("🧠 Analizando con IA...")
            try:
                context = self._build_context(stats, affected_services)
                ai_analysis = self.ollama.analyze_errors(
                    true_errors[:self.config.get('max_errors_for_ai', 10)],
                    context=context
                )
                recommendations = self._extract_recommendations(ai_analysis)
                print("   ✅ Análisis de IA completado")
            except Exception as e:
                print(f"   ⚠️  Error en IA: {e}")
                ai_analysis = f"Error en análisis: {str(e)[:100]}"
        elif use_ai and not self.ai_available:
            ai_analysis = "⚠️ Ollama no disponible. Instala y ejecuta 'ollama serve'"
        
        # 5. Generar reporte
        self._log("Generando reporte...")
        report_data = {
            'statistics': stats,
            'true_errors': true_errors[:20],  # Limitar a 20 para el reporte
            'false_positives': false_positives[:10],
            'severity_summary': severity_summary,
            'error_types_summary': error_types_summary,
            'affected_services': list(affected_services),
            'ai_analysis': ai_analysis,
            'recommendations': recommendations,
            'total_errors_found': len(true_errors),
            'total_false_positives': len(false_positives)
        }
        
        report_file = self.reporter.generate_report(report_data)
        print(f"📄 Reporte generado: {report_file}")
        
        return report_data
    
    def _build_context(self, stats: Dict, affected_services: set) -> str:
        return f"""
Estadísticas:
- Total transacciones: {stats.get('total_transactions', 0)}
- Tasa de éxito: {stats.get('success_rate', 0):.1f}%
- Servicios afectados: {', '.join(affected_services) if affected_services else 'Ninguno'}

Entorno: Kubernetes / Spring Boot / Keycloak
"""
    
    def _extract_recommendations(self, analysis: str) -> List[str]:
        if not analysis:
            return ["Revisar los logs completos para más detalles"]
        
        recommendations = []
        lines = analysis.split('\n')
        in_rec = False
        
        for line in lines:
            if 'recomendacion' in line.lower() or 'RECOMENDACION' in line:
                in_rec = True
                continue
            if in_rec and line.strip().startswith('-'):
                rec = line.strip()[1:].strip()
                if len(rec) > 10:
                    recommendations.append(rec)
            if in_rec and len(line.strip()) > 0 and not line.strip().startswith('-'):
                if len(line.strip()) > 20 and not line.strip().startswith('#'):
                    recommendations.append(line.strip())
            if in_rec and line.strip().startswith('#'):
                break
        
        return recommendations[:5] if recommendations else ["Verificar conectividad con servicios externos"]