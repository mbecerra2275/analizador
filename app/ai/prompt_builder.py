"""
Constructor de prompts para el análisis con IA - VERSIÓN OPTIMIZADA.
"""
from typing import List, Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)

class PromptBuilder:
    """Constructor de prompts optimizado para análisis de logs."""
    
    def __init__(self):
        self.max_errors_to_analyze = 10  # Reducido de 10 a 5 para más velocidad
        self.max_messages_per_error = 2  # Reducido para menos tokens
        self.max_message_length = 200    # Reducido para menos tokens
        
        self.system_prompt = """Eres un experto en análisis de logs de Kubernetes.
Proporciona análisis concisos y recomendaciones prácticas.
"""
    
    def build_error_analysis_prompt(
        self, 
        errors: List[Dict[str, Any]], 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Construye un prompt optimizado para analizar errores.
        """
        if not errors:
            return "No se encontraron errores en el análisis."
        
        # Limitar la cantidad de errores a analizar
        errors_to_analyze = errors[:self.max_errors_to_analyze]
        
        prompt_parts = []
        prompt_parts.append("## Análisis de Errores en Logs")
        prompt_parts.append("")
        
        # Resumen rápido
        prompt_parts.append(f"Total de errores: {len(errors)}")
        if context and context.get('total_groups'):
            prompt_parts.append(f"Total de grupos: {context.get('total_groups')}")
        prompt_parts.append("")
        
        # Mostrar solo los errores más importantes (resumidos)
        prompt_parts.append("### Principales Errores")
        prompt_parts.append("")
        
        for i, error in enumerate(errors_to_analyze[:5], 1):
            corr_id = error.get('correlation_id', 'N/A')
            error_count = error.get('error_count', 0)
            messages = error.get('messages', [])
            
            prompt_parts.append(f"**Error {i}:** {corr_id}")
            prompt_parts.append(f"- Cantidad: {error_count}")
            
            if messages:
                # Solo el primer mensaje y truncado
                first_msg = messages[0][:self.max_message_length]
                if len(messages[0]) > self.max_message_length:
                    first_msg += "..."
                prompt_parts.append(f"- Mensaje: {first_msg}")
            
            # Agregar clasificación rápida
            if messages:
                msg_lower = messages[0].lower()
                if 'connection refused' in msg_lower or 'connect' in msg_lower:
                    prompt_parts.append("- Tipo: Conexión")
                elif 'timeout' in msg_lower or 'timed out' in msg_lower:
                    prompt_parts.append("- Tipo: Timeout")
                elif 'permission' in msg_lower or 'access denied' in msg_lower:
                    prompt_parts.append("- Tipo: Permisos")
                elif 'not found' in msg_lower or 'no such' in msg_lower:
                    prompt_parts.append("- Tipo: Recurso no encontrado")
                elif 'memory' in msg_lower or 'oom' in msg_lower:
                    prompt_parts.append("- Tipo: Memoria")
                else:
                    prompt_parts.append("- Tipo: Otro")
            
            prompt_parts.append("")
        
        if len(errors) > 5:
            prompt_parts.append(f"... y {len(errors) - 5} errores adicionales")
            prompt_parts.append("")
        
        # Instrucciones claras y cortas
        prompt_parts.append("### Tareas")
        prompt_parts.append("1. Identifica los 3 tipos de error más comunes")
        prompt_parts.append("2. Prioriza los errores por severidad")
        prompt_parts.append("3. Da 3-5 recomendaciones concretas")
        prompt_parts.append("")
        
        prompt_parts.append("### Respuesta (máximo 300 palabras)")
        prompt_parts.append("Proporciona un análisis breve con:")
        prompt_parts.append("- Resumen ejecutivo (1-2 oraciones)")
        prompt_parts.append("- Top 3 problemas")
        prompt_parts.append("- Recomendaciones prácticas")
        
        return "\n".join(prompt_parts)
    
    def build_recommendations_prompt(self, errors: List[Dict[str, Any]]) -> str:
        """Construye un prompt optimizado para recomendaciones."""
        if not errors:
            return "No se encontraron errores."
        
        prompt_parts = []
        prompt_parts.append("## Recomendaciones")
        prompt_parts.append("")
        prompt_parts.append(f"Errores detectados: {len(errors)}")
        prompt_parts.append("")
        
        # Agrupar errores por tipo
        error_types = {}
        for error in errors[:10]:
            messages = error.get('messages', [])
            if messages:
                msg = messages[0].lower()
                if 'connection' in msg or 'connect' in msg:
                    error_types['Conexión'] = error_types.get('Conexión', 0) + 1
                elif 'timeout' in msg:
                    error_types['Timeout'] = error_types.get('Timeout', 0) + 1
                elif 'permission' in msg or 'access' in msg:
                    error_types['Permisos'] = error_types.get('Permisos', 0) + 1
                elif 'not found' in msg:
                    error_types['Recurso no encontrado'] = error_types.get('Recurso no encontrado', 0) + 1
                else:
                    error_types['Otros'] = error_types.get('Otros', 0) + 1
        
        if error_types:
            prompt_parts.append("### Tipos de errores:")
            for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                prompt_parts.append(f"- {error_type}: {count}")
            prompt_parts.append("")
        
        prompt_parts.append("### Proporciona:")
        prompt_parts.append("1. 3 acciones inmediatas")
        prompt_parts.append("2. 2 mejoras a corto plazo")
        prompt_parts.append("3. 1 recomendación estructural")
        
        return "\n".join(prompt_parts)
    
    def build_classification_prompt(self, error: Dict[str, Any]) -> str:
        """Construye un prompt corto para clasificar un error."""
        messages = error.get('messages', [])
        first_msg = messages[0][:200] if messages else "Sin mensaje"
        
        prompt_parts = []
        prompt_parts.append("Clasifica este error:")
        prompt_parts.append(f"Mensaje: {first_msg}")
        prompt_parts.append("")
        prompt_parts.append("Categorías: Conexión, Timeout, Permisos, Recurso no encontrado, Otro")
        prompt_parts.append("Severidad: Crítica, Alta, Media, Baja")
        prompt_parts.append("")
        prompt_parts.append("Responde con: Categoría, Severidad, Recomendación breve")
        
        return "\n".join(prompt_parts)