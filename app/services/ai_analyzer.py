"""
Servicio de análisis con IA.
"""
import logging
from typing import Dict, Any, Optional, List

from ..ai.ollama_client import OllamaClient
from ..ai.prompt_builder import PromptBuilder
from ..models.correlation_group import CorrelationGroup

logger = logging.getLogger(__name__)

class AIAnalyzer:
    """Analizador de logs con IA."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el analizador de IA.
        
        Args:
            config: Diccionario de configuración
        """
        self.config = config
        self.client = OllamaClient(
            base_url=config.get('ollama_url', 'http://127.0.0.1:11434'),
            timeout=config.get('ollama_timeout', 45),
            connection_timeout=config.get('ollama_connection_timeout', 10),
            max_retries=config.get('ollama_max_retries', 5)
        )
        self.prompt_builder = PromptBuilder()
        self._available = None
    
    @property
    def is_available(self) -> bool:
        """Verifica si la IA está disponible."""
        if self._available is None:
            diagnostic = self.client.test_connection()
            self._available = diagnostic.is_available
            if not self._available:
                logger.warning("⚠️ IA no disponible")
        return self._available
    
    def analyze_errors(
        self, 
        errors: List[Dict[str, Any]], 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analiza errores con IA.
        
        Args:
            errors: Lista de errores a analizar
            context: Contexto adicional (opcional)
        
        Returns:
            Diccionario con el análisis
        """
        if not self.is_available:
            return {
                'status': 'offline',
                'analysis': '⚠️ Análisis IA no disponible - Ollama no está corriendo',
                'errors_analyzed': len(errors)
            }
        
        if not errors:
            return {
                'status': 'success',
                'analysis': '✅ No se encontraron errores para analizar',
                'errors_analyzed': 0
            }
        
        try:
            # Construir prompt
            prompt = self.prompt_builder.build_error_analysis_prompt(errors, context)
            logger.debug(f"Prompt generado, longitud: {len(prompt)} caracteres")
            
            # Generar análisis
            response = self.client.generate(
                prompt,
                temperature=self.config.get('ollama_temperature', 0.3),
                num_predict=self.config.get('ollama_num_predict', 500)
            )
            
            if response:
                return {
                    'status': 'success',
                    'analysis': response,
                    'errors_analyzed': len(errors)
                }
            else:
                return {
                    'status': 'partial',
                    'analysis': '⚠️ La IA no pudo generar un análisis completo',
                    'errors_analyzed': len(errors)
                }
                
        except Exception as e:
            logger.error(f"Error en análisis IA: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'analysis': f'⚠️ Error en análisis IA: {str(e)}',
                'errors_analyzed': len(errors)
            }
    
    def get_recommendations(self, errors: List[Dict[str, Any]]) -> List[str]:
        """
        Obtiene recomendaciones para los errores.
        
        Args:
            errors: Lista de errores
            
        Returns:
            Lista de recomendaciones
        """
        if not self.is_available or not errors:
            return ["Revisar logs manualmente (IA no disponible)"]
        
        try:
            prompt = self.prompt_builder.build_recommendations_prompt(errors)
            response = self.client.generate(prompt, num_predict=300)
            
            if response:
                # Dividir en líneas y filtrar
                recommendations = []
                lines = response.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and any(keyword in line.lower() for keyword in 
                                  ['recomend', 'suger', 'consid', 'verificar', 'revisar', 'acción', 'paso']):
                        recommendations.append(line)
                
                if recommendations:
                    return recommendations
                else:
                    # Si no hay recomendaciones claras, devolver todo
                    return [response[:500]]
            
        except Exception as e:
            logger.error(f"Error obteniendo recomendaciones: {str(e)}")
        
        return ["No se pudieron generar recomendaciones automáticas"]
    
    def classify_error(self, error: Dict[str, Any]) -> Dict[str, str]:
        """
        Clasifica un error individual.
        
        Args:
            error: Diccionario con el error
            
        Returns:
            Diccionario con la clasificación
        """
        if not self.is_available:
            return {
                'category': 'Desconocida',
                'severity': 'Media',
                'cause': 'No disponible (IA offline)',
                'solution': 'Revisar manualmente'
            }
        
        try:
            prompt = self.prompt_builder.build_error_classification_prompt(error)
            response = self.client.generate(prompt, num_predict=200)
            
            if response:
                # Parsear la respuesta (simple)
                lines = response.split('\n')
                result = {
                    'category': 'Otro',
                    'severity': 'Media',
                    'cause': 'No especificada',
                    'solution': 'Revisar logs'
                }
                
                for line in lines:
                    line_lower = line.lower()
                    if 'categoría' in line_lower or 'categoria' in line_lower or 'category' in line_lower:
                        if 'conexión' in line_lower or 'connection' in line_lower:
                            result['category'] = 'Conexión'
                        elif 'timeout' in line_lower:
                            result['category'] = 'Timeout'
                        elif 'permiso' in line_lower or 'permission' in line_lower:
                            result['category'] = 'Permisos'
                        elif 'no encontrado' in line_lower or 'not found' in line_lower:
                            result['category'] = 'Recurso no encontrado'
                        elif 'base de datos' in line_lower or 'database' in line_lower:
                            result['category'] = 'Base de datos'
                        elif 'memoria' in line_lower or 'memory' in line_lower:
                            result['category'] = 'Memoria'
                    
                    if 'severidad' in line_lower or 'severity' in line_lower:
                        if 'crítica' in line_lower or 'critical' in line_lower:
                            result['severity'] = 'Crítica'
                        elif 'alta' in line_lower or 'high' in line_lower:
                            result['severity'] = 'Alta'
                        elif 'media' in line_lower or 'medium' in line_lower:
                            result['severity'] = 'Media'
                        elif 'baja' in line_lower or 'low' in line_lower:
                            result['severity'] = 'Baja'
                
                return result
            
        except Exception as e:
            logger.error(f"Error clasificando error: {str(e)}")
        
        return {
            'category': 'Otro',
            'severity': 'Media',
            'cause': 'Error en clasificación',
            'solution': 'Revisar logs manualmente'
        }
    
    def generate_summary(self, summary: Dict[str, Any], errors: List[Dict[str, Any]]) -> Optional[str]:
        """
        Genera un resumen ejecutivo.
        
        Args:
            summary: Resumen estadístico
            errors: Lista de errores
            
        Returns:
            Resumen ejecutivo o None si falla
        """
        if not self.is_available:
            return None
        
        try:
            prompt = self.prompt_builder.build_summary_prompt(summary, errors)
            response = self.client.generate(prompt, num_predict=200)
            return response
        except Exception as e:
            logger.error(f"Error generando resumen: {str(e)}")
            return None