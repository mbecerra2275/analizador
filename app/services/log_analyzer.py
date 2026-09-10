# app/services/log_analyzer.py
import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from pathlib import Path, WindowsPath, PosixPath
from concurrent.futures import ThreadPoolExecutor, as_completed

# Importar desde tu estructura
from app.core.log_parser import LogParser
from app.core.log_splitter import LogSplitter
from app.core.smart_filter import SmartFilter
from app.core.correlation_analyzer import CorrelationAnalyzer
from app.models.error_report import ErrorReport
from app.reporters.markdown_reporter import MarkdownReporter
from app.services.ai_analyzer import AIAnalyzerService
from app.utils.file_utils import FileUtils
from app.config import Config

logger = logging.getLogger(__name__)

# Helper para serialización JSON
class DateTimeEncoder(json.JSONEncoder):
    """Encoder personalizado para datetime y Path"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, (WindowsPath, PosixPath, Path)):
            return str(obj)
        if hasattr(obj, '__dict__'):
            return str(obj)
        return super().default(obj)

class LogAnalyzerService:
    """Servicio principal de análisis de logs"""
    
    def __init__(self):
        # Inicializar componentes
        self.log_splitter = LogSplitter() if hasattr(LogSplitter, '__init__') else LogSplitter
        self.smart_filter = SmartFilter()
        self.reporter = MarkdownReporter()
        self.ai_service = AIAnalyzerService()
        
    def analyze_log_file(self, file_path: str, use_ai: bool = True) -> Dict[str, Any]:
        """Analiza un archivo de log completo"""
        try:
            logger.info(f"Iniciando análisis de: {file_path}")
            
            # Leer archivo
            content = FileUtils.read_file(file_path)
            lines = content.split('\n')
            
            # Crear parser con las líneas
            log_parser = LogParser(lines)
            log_entries = log_parser.parse_lines(lines)
            
            # Detectar errores
            errors = log_parser.get_errors()
            
            # Filtrar inteligentemente
            filtered_errors = self.smart_filter.filter_errors(errors) if hasattr(self.smart_filter, 'filter_errors') else errors
            
            # Correlacionar errores
            correlation_analyzer = CorrelationAnalyzer(filtered_errors)
            correlations = correlation_analyzer.analyze()
            
            # Generar estadísticas
            stats = self._generate_statistics(lines, errors)
            stats['parser_stats'] = log_parser.get_statistics()
            if hasattr(correlation_analyzer, 'get_correlation_summary'):
                stats['correlations'] = correlation_analyzer.get_correlation_summary()
            
            # Análisis con IA
            ai_analysis = None
            if use_ai and errors:
                try:
                    ai_analysis = self.ai_service.analyze_errors(errors[:50])
                except Exception as e:
                    logger.warning(f"Error en análisis IA: {str(e)}")
                    ai_analysis = {"error": str(e)}
            
            # Generar reporte
            report_path = self._generate_report(
                file_path=file_path,
                stats=stats,
                errors=errors,
                correlations=correlations,
                ai_analysis=ai_analysis
            )
            
            return {
                "file_name": os.path.basename(file_path),
                "total_lines": len(lines),
                "error_count": len(errors),
                "statistics": stats,
                "errors": errors[:100],
                "ai_analysis": ai_analysis,
                "report_file": report_path
            }
            
        except Exception as e:
            logger.error(f"Error en análisis: {str(e)}")
            raise

    def analyze_with_multi_ai(
        self,
        file_path: str,
        models: Optional[List[str]] = None,
        block_size: int = 5000
    ) -> Dict[str, Any]:
        """Analiza el archivo en bloques usando múltiples modelos IA"""
        try:
            logger.info(f"Iniciando análisis multi-IA de: {file_path}")
            
            if not models:
                models = ['ollama', 'openai', 'groq']
            
            # Leer archivo
            content = FileUtils.read_file(file_path)
            lines = content.split('\n')
            total_lines = len(lines)
            
            # Dividir en bloques
            blocks = []
            for i in range(0, total_lines, block_size):
                block = {
                    'start_line': i,
                    'end_line': min(i + block_size, total_lines),
                    'content': lines[i:min(i + block_size, total_lines)]
                }
                blocks.append(block)
            
            logger.info(f"Archivo dividido en {len(blocks)} bloques de {block_size} líneas")
            
            # Procesar cada bloque
            model_results = {}
            block_results = []
            
            with ThreadPoolExecutor(max_workers=min(len(models), 4)) as executor:
                futures = {}
                
                for idx, block in enumerate(blocks):
                    model = models[idx % len(models)]
                    block_context = {
                        "block_id": idx + 1,
                        "lines": block['content'],
                        "start_line": block['start_line'],
                        "end_line": block['end_line'],
                        "total_lines": len(block['content'])
                    }
                    
                    future = executor.submit(
                        self._analyze_block_with_model,
                        block_context,
                        model
                    )
                    futures[future] = (idx + 1, model)
                
                for future in as_completed(futures):
                    block_id, model = futures[future]
                    try:
                        result = future.result(timeout=120)
                        model_results[model] = result
                        block_results.append({
                            "block_id": block_id,
                            "model": model,
                            "result": result
                        })
                        logger.info(f"Bloque {block_id} analizado con {model}")
                    except Exception as e:
                        logger.error(f"Error en bloque {block_id} con {model}: {str(e)}")
                        model_results[model] = {"error": str(e)}
            
            # Generar reporte
            report_path = self._generate_multi_ai_report(
                file_path=file_path,
                blocks=blocks,
                model_results=model_results
            )
            
            return {
                "blocks": len(blocks),
                "total_lines": total_lines,
                "models_used": list(model_results.keys()),
                "model_results": model_results,
                "report_file": report_path,
                "success_rate": sum(1 for r in model_results.values() if "error" not in r) / len(model_results) if model_results else 0
            }
            
        except Exception as e:
            logger.error(f"Error en análisis multi-IA: {str(e)}")
            raise

    def _analyze_block_with_model(self, block_context: Dict[str, Any], model: str) -> Dict[str, Any]:
        """Analiza un bloque con un modelo específico"""
        try:
            # Parsear el bloque
            log_parser = LogParser(block_context['lines'])
            log_entries = log_parser.parse_lines(block_context['lines'])
            
            # Detectar errores
            errors = log_parser.get_errors()
            
            # Analizar con IA
            ai_result = self.ai_service.analyze_with_model(
                errors=errors[:20],
                model=model,
                context=block_context
            )
            
            return {
                "total_lines": block_context['total_lines'],
                "errors_found": len(errors),
                "error_details": errors[:10],
                "ai_analysis": ai_result,
                "patterns_detected": self._extract_patterns(ai_result),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error en análisis con modelo {model}: {str(e)}")
            return {"error": str(e)}

    def _extract_patterns(self, ai_result: Dict[str, Any]) -> List[str]:
        """Extrae patrones del resultado de IA"""
        if isinstance(ai_result, dict):
            patterns = ai_result.get('patterns', [])
            if not patterns:
                for key in ['common_patterns', 'error_patterns', 'patterns_found']:
                    if key in ai_result and isinstance(ai_result[key], list):
                        return ai_result[key]
            return patterns
        return []

    def _generate_statistics(self, lines: List[str], errors: List[Dict]) -> Dict[str, Any]:
        """Genera estadísticas del log"""
        stats = {
            'total_lines': len(lines),
            'empty_lines': sum(1 for l in lines if not l.strip()),
            'error_count': len(errors),
        }
        
        severity_counts = {}
        for error in errors:
            severity = error.get('severity', 'UNKNOWN')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        stats['severity_distribution'] = severity_counts
        
        return stats

    def _prepare_serializable(self, obj: Any) -> Any:
        """Prepara un objeto para serialización JSON"""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, (WindowsPath, PosixPath, Path)):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: self._prepare_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._prepare_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return str(obj)
        else:
            return obj

    def _generate_report(self, file_path: str, stats: Dict, errors: List,
                        correlations: List, ai_analysis: Dict) -> str:
        """Genera un reporte del análisis"""
        Config.ensure_directories()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = Path(file_path).stem
        report_path = Config.REPORTS_DIR / f"report_{base_name}_{timestamp}.md"
        
        # Intentar usar el reporter Markdown
        try:
            if hasattr(self.reporter, 'generate'):
                self.reporter.generate(
                    report_path=str(report_path),
                    file_path=file_path,
                    stats=stats,
                    errors=errors,
                    correlations=correlations,
                    ai_analysis=ai_analysis
                )
                return str(report_path)
            else:
                raise AttributeError("generate method not found")
        except Exception as e:
            logger.warning(f"Error generando reporte Markdown: {e}")
            # Fallback a JSON con encoder personalizado
            report_path = report_path.with_suffix('.json')
            
            # Preparar datos para JSON
            report_data = {
                'file': str(file_path),  # Convertir a string explícitamente
                'timestamp': timestamp,
                'stats': self._prepare_serializable(stats),
                'errors': self._prepare_serializable(errors[:50]),
                'correlations': self._prepare_serializable(correlations[:20] if correlations else []),
                'ai_analysis': self._prepare_serializable(ai_analysis)
            }
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
            
            return str(report_path)

    def _generate_multi_ai_report(self, file_path: str, blocks: List,
                                 model_results: Dict) -> str:
        """Genera un reporte multi-IA"""
        Config.ensure_directories()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = Path(file_path).stem
        report_path = Config.REPORTS_DIR / f"multi_ai_{base_name}_{timestamp}.json"
        
        report_data = {
            "analysis_type": "multi_ai",
            "file": str(file_path),  # Convertir a string explícitamente
            "timestamp": timestamp,
            "total_blocks": len(blocks),
            "models_used": list(model_results.keys()),
            "model_results": self._prepare_serializable(model_results)
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
        
        return str(report_path)