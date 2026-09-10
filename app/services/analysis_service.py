"""
Servicio principal de análisis de logs.
"""
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..core.log_parser import LogParser
from ..core.correlation_analyzer import CorrelationAnalyzer
from ..core.smart_filter import SmartFilter
from ..services.ai_analyzer import AIAnalyzer
from ..reporters.markdown_reporter import MarkdownReporter
from ..utils.file_utils import FileUtils
from ..config import Config

logger = logging.getLogger(__name__)

class AnalysisService:
    """Servicio principal de análisis de logs."""
    
    def __init__(self, config: Optional[Config] = None):
        """
        Inicializa el servicio de análisis.
        
        Args:
            config: Configuración de la aplicación
        """
        self.config = config or Config()
        self.parser = LogParser()
        self.correlator = CorrelationAnalyzer()
        self.filter = SmartFilter()
        self.reporter = MarkdownReporter()
        self.file_utils = FileUtils()
        
        # Inicializar AI Analyzer con la configuración
        if hasattr(self.config, 'to_dict'):
            config_dict = self.config.to_dict()
        else:
            config_dict = {
                'ollama_url': 'http://127.0.0.1:11434',
                'ollama_model': 'qwen2.5-coder:1.5b',
                'ollama_timeout': 45,
                'ollama_max_retries': 5
            }
        
        self.ai_analyzer = AIAnalyzer(config_dict)
        
        logger.info("AnalysisService inicializado correctamente")
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analiza un archivo de logs completo.
        
        Args:
            file_path: Ruta al archivo de logs
            
        Returns:
            Diccionario con los resultados del análisis
        """
        logger.info(f"📊 Iniciando análisis de: {file_path}")
        
        # Validar archivo
        path = Path(file_path)
        if not path.exists():
            error_msg = f"Archivo no encontrado: {file_path}"
            logger.error(error_msg)
            return {
                'file': file_path,
                'error': error_msg,
                'total_logs': 0,
                'total_groups': 0,
                'filtered_groups': 0,
                'errors': [],
                'ai_analysis': {'status': 'error', 'analysis': error_msg}
            }
        
        if path.stat().st_size == 0:
            error_msg = f"El archivo está vacío: {file_path}"
            logger.error(error_msg)
            return {
                'file': file_path,
                'error': error_msg,
                'total_logs': 0,
                'total_groups': 0,
                'filtered_groups': 0,
                'errors': [],
                'ai_analysis': {'status': 'error', 'analysis': error_msg}
            }
        
        try:
            # 1. Cargar logs
            logger.info("📂 Cargando archivo...")
            raw_logs = self.file_utils.read_file(file_path)
            
            if not raw_logs:
                error_msg = "El archivo está vacío o no se pudo leer"
                logger.error(error_msg)
                return {
                    'file': file_path,
                    'error': error_msg,
                    'total_logs': 0,
                    'total_groups': 0,
                    'filtered_groups': 0,
                    'errors': [],
                    'ai_analysis': {'status': 'error', 'analysis': error_msg}
                }
            
            logger.info(f"📄 Archivo leído: {len(raw_logs)} caracteres")
            
            # 2. Parsear logs
            logger.info("🔄 Parseando logs...")
            parsed_logs = self.parser.parse(raw_logs)
            logger.info(f"✅ Parseados {len(parsed_logs)} logs")
            
            if not parsed_logs:
                logger.warning("⚠️ No se pudieron parsear logs del archivo")
                return {
                    'file': file_path,
                    'error': 'No se pudieron parsear logs del archivo',
                    'total_logs': 0,
                    'total_groups': 0,
                    'filtered_groups': 0,
                    'errors': [],
                    'ai_analysis': {'status': 'offline', 'analysis': 'No se encontraron logs parseables'}
                }
            
            # 3. Correlacionar por ID
            logger.info("🔗 Correlacionando logs...")
            groups = self.correlator.group_by_correlation(parsed_logs)
            logger.info(f"✅ {len(groups)} transacciones/grupos identificados")
            
            # 4. Filtrar falsos positivos
            logger.info("🔍 Filtrando falsos positivos...")
            filtered_groups = self.filter.filter_groups(groups)
            logger.info(f"✅ {len(filtered_groups)} grupos después de filtrado (descartados {len(groups) - len(filtered_groups)})")
            
            # 5. Extraer errores
            logger.info("⚠️ Extrayendo errores...")
            errors = self._extract_errors(filtered_groups)
            logger.info(f"✅ {len(errors)} errores detectados")
            
            # 6. Analizar con IA (si está disponible)
            logger.info("🤖 Generando análisis con IA...")
            ai_analysis = self._run_ai_analysis(errors, filtered_groups)
            
            # 7. Generar recomendaciones
            recommendations = self._generate_recommendations(errors, ai_analysis)
            
            # 8. Construir reporte
            report = {
                'file': str(file_path),
                'total_logs': len(parsed_logs),
                'total_groups': len(groups),
                'filtered_groups': len(filtered_groups),
                'errors': errors,
                'ai_analysis': ai_analysis,
                'recommendations': recommendations,
                'summary': self._generate_summary(parsed_logs, groups, filtered_groups, errors)
            }
            
            # 9. Generar reporte Markdown
            logger.info("📝 Generando reporte Markdown...")
            try:
                report_path = self.reporter.generate(report)
                report['report_path'] = report_path
                logger.info(f"✅ Reporte guardado: {report_path}")
            except Exception as e:
                logger.error(f"❌ Error generando reporte: {str(e)}")
                report['report_path'] = None
                report['report_error'] = str(e)
            
            logger.info("✅ Análisis completado exitosamente")
            return report
            
        except Exception as e:
            error_msg = f"Error durante el análisis: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                'file': file_path,
                'error': error_msg,
                'total_logs': 0,
                'total_groups': 0,
                'filtered_groups': 0,
                'errors': [],
                'ai_analysis': {
                    'status': 'error',
                    'analysis': f'Error: {str(e)}'
                }
            }
    
    def _extract_errors(self, groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extrae errores de los grupos de logs.
        
        Args:
            groups: Lista de grupos de logs
            
        Returns:
            Lista de errores encontrados
        """
        errors = []
        
        for group in groups:
            # Verificar si el grupo tiene errores
            if group.get('has_errors', False):
                error_entry = {
                    'correlation_id': group.get('correlation_id', 'N/A'),
                    'error_count': group.get('error_count', 0),
                    'timestamp': group.get('timestamp', ''),
                    'messages': group.get('error_messages', []),
                    'levels': group.get('levels', []),
                    'total_entries': group.get('count', 0)
                }
                errors.append(error_entry)
        
        # Ordenar errores por cantidad (más errores primero)
        errors.sort(key=lambda x: x.get('error_count', 0), reverse=True)
        
        return errors
    
    def _run_ai_analysis(self, errors: List[Dict[str, Any]], groups: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Ejecuta el análisis con IA.
        
        Args:
            errors: Lista de errores encontrados
            groups: Lista de grupos de logs
            
        Returns:
            Resultados del análisis con IA
        """
        try:
            if not errors:
                return {
                    'status': 'success',
                    'analysis': '✅ No se encontraron errores. Todo funciona correctamente.',
                    'errors_analyzed': 0
                }
            
            # Verificar si la IA está disponible
            if not self.ai_analyzer.is_available:
                return {
                    'status': 'offline',
                    'analysis': '⚠️ Análisis IA no disponible - Ollama no está corriendo o no responde',
                    'errors_analyzed': len(errors)
                }
            
            # Preparar contexto para la IA
            context = {
                'total_errors': len(errors),
                'total_groups': len(groups),
                'error_summary': [{
                    'id': e.get('correlation_id', 'N/A'),
                    'count': e.get('error_count', 0),
                    'sample': e.get('messages', [''])[0][:100] if e.get('messages') else ''
                } for e in errors[:5]]
            }
            
            # Ejecutar análisis
            ai_result = self.ai_analyzer.analyze_errors(errors, context)
            
            # Si el análisis devolvió éxito, usarlo
            if ai_result and ai_result.get('status') == 'success':
                return ai_result
            else:
                # Análisis básico de fallback
                return {
                    'status': 'partial',
                    'analysis': self._generate_fallback_analysis(errors),
                    'errors_analyzed': len(errors)
                }
                
        except Exception as e:
            logger.error(f"❌ Error en análisis IA: {str(e)}")
            return {
                'status': 'error',
                'analysis': f'⚠️ Error en análisis IA: {str(e)}',
                'errors_analyzed': len(errors)
            }
    
    def _generate_fallback_analysis(self, errors: List[Dict[str, Any]]) -> str:
        """
        Genera un análisis básico sin IA.
        
        Args:
            errors: Lista de errores
            
        Returns:
            Análisis en formato texto
        """
        if not errors:
            return "✅ No se encontraron errores."
        
        analysis = []
        analysis.append(f"⚠️ Se encontraron {len(errors)} grupos con errores:")
        
        for i, error in enumerate(errors[:10], 1):
            corr_id = error.get('correlation_id', 'N/A')
            count = error.get('error_count', 0)
            messages = error.get('messages', [])
            
            analysis.append(f"\n{i}. Correlation ID: {corr_id}")
            analysis.append(f"   Errores: {count}")
            
            if messages:
                first_msg = messages[0]
                if len(first_msg) > 150:
                    first_msg = first_msg[:150] + "..."
                analysis.append(f"   Mensaje: {first_msg}")
        
        if len(errors) > 10:
            analysis.append(f"\n... y {len(errors) - 10} errores más")
        
        analysis.append("\n💡 Recomendación: Revisar los logs para más detalles")
        
        return "\n".join(analysis)
    
    def _generate_recommendations(self, errors: List[Dict[str, Any]], ai_analysis: Dict[str, Any]) -> List[str]:
        """
        Genera recomendaciones basadas en los errores y análisis IA.
        
        Args:
            errors: Lista de errores
            ai_analysis: Análisis de IA
            
        Returns:
            Lista de recomendaciones
        """
        recommendations = []
        
        # Si no hay errores
        if not errors:
            recommendations.append("✅ No se encontraron errores. El sistema parece funcionar correctamente.")
            return recommendations
        
        # Recomendaciones de IA (si están disponibles)
        if ai_analysis.get('status') == 'success':
            ai_text = ai_analysis.get('analysis', '')
            if ai_text:
                # Dividir en líneas y tomar las que parecen recomendaciones
                lines = ai_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and any(keyword in line.lower() for keyword in 
                                  ['recomend', 'suger', 'solución', 'debería', 'puede', 'considera', 'verificar']):
                        recommendations.append(line)
                if recommendations:
                    return recommendations
        
        # Recomendaciones basadas en tipos de errores
        error_types = self._categorize_errors(errors)
        
        for error_type, count in error_types.items():
            if error_type == 'connection':
                recommendations.append(f"🔌 Se detectaron {count} errores de conexión. Verificar la conectividad de red y firewalls.")
            elif error_type == 'timeout':
                recommendations.append(f"⏱️ Se detectaron {count} timeouts. Considerar aumentar los timeouts o escalar los servicios.")
            elif error_type == 'permission':
                recommendations.append(f"🔒 Se detectaron {count} errores de permisos. Verificar roles, políticas y credenciales.")
            elif error_type == 'not_found':
                recommendations.append(f"🔍 Se detectaron {count} errores de recursos no encontrados. Verificar URLs, rutas y nombres de servicios.")
            elif error_type == 'database':
                recommendations.append(f"💾 Se detectaron {count} errores de base de datos. Verificar conexión, estado y consultas.")
            elif error_type == 'memory':
                recommendations.append(f"🧠 Se detectaron {count} errores de memoria. Considerar aumentar límites o optimizar uso.")
            elif error_type == 'disk':
                recommendations.append(f"💿 Se detectaron {count} errores de disco. Verificar espacio disponible y permisos de escritura.")
        
        if not recommendations:
            recommendations.append("📋 Revisar los logs manualmente para identificar la causa raíz.")
            recommendations.append("💡 Considerar activar logs más detallados para debug.")
        
        return recommendations
    
    def _categorize_errors(self, errors: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Categoriza los errores por tipo.
        
        Args:
            errors: Lista de errores
            
        Returns:
            Diccionario con conteo por tipo
        """
        categories = {
            'connection': 0,
            'timeout': 0,
            'permission': 0,
            'not_found': 0,
            'database': 0,
            'memory': 0,
            'disk': 0,
            'other': 0
        }
        
        keywords = {
            'connection': ['connection', 'connect', 'refused', 'unreachable', 'network', 'socket'],
            'timeout': ['timeout', 'timed out', 'slow', 'deadline'],
            'permission': ['permission', 'access denied', 'forbidden', 'unauthorized', 'auth'],
            'not_found': ['not found', 'does not exist', 'missing', '404'],
            'database': ['database', 'db', 'sql', 'query', 'postgres', 'mysql', 'mongodb'],
            'memory': ['memory', 'out of memory', 'oom', 'heap', 'stack'],
            'disk': ['disk', 'storage', 'space', 'volume', 'filesystem']
        }
        
        for error in errors:
            messages = error.get('messages', [])
            categorized = False
            
            for msg in messages:
                msg_lower = msg.lower()
                for category, words in keywords.items():
                    if any(word in msg_lower for word in words):
                        categories[category] += 1
                        categorized = True
                        break
                if categorized:
                    break
            
            if not categorized:
                categories['other'] += 1
        
        # Eliminar categorías con 0
        return {k: v for k, v in categories.items() if v > 0}
    
    def _generate_summary(self, parsed_logs: List, groups: List, filtered_groups: List, errors: List) -> Dict[str, Any]:
        """
        Genera un resumen estadístico del análisis.
        
        Args:
            parsed_logs: Logs parseados
            groups: Grupos de correlación
            filtered_groups: Grupos filtrados
            errors: Errores encontrados
            
        Returns:
            Diccionario con estadísticas
        """
        # Niveles de log
        levels = {}
        for log in parsed_logs:
            level = log.get('level', 'INFO').upper()
            levels[level] = levels.get(level, 0) + 1
        
        return {
            'total_logs': len(parsed_logs),
            'total_groups': len(groups),
            'filtered_groups': len(filtered_groups),
            'total_errors': len(errors),
            'levels': levels,
            'error_groups': len([g for g in filtered_groups if g.get('has_errors', False)]),
            'logs_with_correlation': len([l for l in parsed_logs if l.get('correlation_id')])
        }
    
    def get_available_models(self) -> List[str]:
        """
        Obtiene los modelos de IA disponibles.
        
        Returns:
            Lista de modelos disponibles
        """
        if hasattr(self.ai_analyzer, 'client'):
            return self.ai_analyzer.client.list_models()
        return []
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Prueba la conexión con Ollama.
        
        Returns:
            Resultado de la prueba de conexión
        """
        if hasattr(self.ai_analyzer, 'client'):
            return self.ai_analyzer.client.test_connection()
        return {'error': 'AI Analyzer no disponible'}