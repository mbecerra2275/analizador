# app/services/ai_analyzer.py
import logging
import json
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict
import re

from app.ai.ollama_client import OllamaClient
from app.ai.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)

class AIAnalyzerService:
    """Servicio de análisis con IA mejorado"""
    
    def __init__(self):
        self.ollama_client = OllamaClient()
        self.prompt_builder = PromptBuilder()
    
    def analyze_errors(self, errors: List[Dict[str, Any]], context: Dict = None) -> Dict[str, Any]:
        """
        Analiza errores usando IA con un enfoque estructurado
        
        Args:
            errors: Lista de errores
            context: Contexto adicional (tipo de app, etc.)
            
        Returns:
            Análisis estructurado de IA
        """
        try:
            # 1. AGRUPAR errores por tipo/patrón antes de enviar a la IA
            grouped_errors = self._group_errors(errors)
            
            # 2. SELECCIONAR los más representativos (no todos)
            representative = self._select_representative_errors(grouped_errors, max_total=15)
            
            # 3. CONSTRUIR un prompt claro y estructurado
            prompt = self._build_structured_prompt(representative, context)
            
            # 4. LLAMAR al modelo con parámetros óptimos
            result = self._call_model_with_retry(prompt)
            
            # 5. VALIDAR y ESTRUCTURAR la respuesta
            structured = self._validate_and_structure(result, grouped_errors)
            
            return structured
            
        except Exception as e:
            logger.error(f"Error en análisis IA: {str(e)}")
            return {
                "error": str(e),
                "status": "failed"
            }
    
    def _group_errors(self, errors: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """
        Agrupa errores por patrones similares para reducir redundancia
        
        Returns:
            Diccionario con grupos de errores
        """
        groups = defaultdict(list)
        
        for error in errors:
            message = error.get('message', error.get('raw', '')).lower()
            severity = error.get('severity', 'UNKNOWN')
            
            # Normalizar el mensaje para agrupar similares
            # Eliminar timestamps, IDs, números
            normalized = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\.\d+Z?', '', message)
            normalized = re.sub(r'[0-9a-f]{8,}', 'ID', normalized)
            normalized = re.sub(r'\d+', 'N', normalized)
            normalized = re.sub(r'\s+', ' ', normalized).strip()
            
            # Crear clave de grupo
            key = f"{severity}:{normalized[:120]}"
            groups[key].append(error)
        
        return dict(groups)
    
    def _select_representative_errors(self, grouped_errors: Dict[str, List], max_total: int = 15) -> List[Dict]:
        """
        Selecciona los errores más representativos de cada grupo
        
        Returns:
            Lista de errores representativos con su frecuencia
        """
        representatives = []
        
        # Ordenar grupos por frecuencia
        sorted_groups = sorted(
            grouped_errors.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        for key, group in sorted_groups[:max_total]:
            # Tomar el primer error como representante
            rep = group[0].copy()
            rep['group_count'] = len(group)
            rep['group_key'] = key
            # Agregar un par de ejemplos más del mismo grupo
            rep['examples'] = [e.get('message', e.get('raw', ''))[:200] for e in group[:3]]
            representatives.append(rep)
        
        return representatives
    
    def _build_structured_prompt(self, errors: List[Dict], context: Dict = None) -> str:
        """
        Construye un prompt claro y estructurado para el modelo
        """
        # Preparar resumen de errores
        error_summary = []
        for i, err in enumerate(errors, 1):
            severity = err.get('severity', 'UNKNOWN')
            count = err.get('group_count', 1)
            message = err.get('message', err.get('raw', ''))[:150]
            error_summary.append(f"{i}. [{severity}] (x{count}) {message}")
        
        errors_text = '\n'.join(error_summary)
        
        # Info de contexto
        context_info = ""
        if context:
            if 'file_name' in context:
                context_info += f"\nArchivo analizado: {context['file_name']}"
            if 'app_type' in context:
                context_info += f"\nTipo de aplicación: {context['app_type']}"
        
        prompt = f"""Eres un ingeniero SRE senior especializado en análisis de logs. Analiza los siguientes errores agrupados por patrón.

CONTEXTO:{context_info}
Total de grupos de errores únicos: {len(errors)}

ERRORES MÁS FRECUENTES (ordenados por frecuencia):
{errors_text}

INSTRUCCIONES:
Responde ÚNICAMENTE con un JSON válido, sin explicaciones adicionales, con esta estructura exacta:

{{
  "resumen_ejecutivo": "Una frase corta (máx 150 caracteres) describiendo el problema principal",
  "severidad_global": "CRITICAL|HIGH|MEDIUM|LOW",
  "categorias": [
    {{
      "nombre": "Categoría del problema (ej: Conexión BD, Timeout API, NullPointer, etc.)",
      "frecuencia": "porcentaje o número aproximado",
      "severidad": "CRITICAL|HIGH|MEDIUM|LOW",
      "descripcion": "Qué está pasando (máx 100 caracteres)",
      "causa_probable": "La causa más probable (máx 100 caracteres)",
      "evidencia": "Los patrones del log que sustentan esto"
    }}
  ],
  "patrones_clave": [
    "Patrón 1 detectado (mensaje específico y reconocible)",
    "Patrón 2 detectado"
  ],
  "acciones_recomendadas": [
    {{
      "prioridad": "ALTA|MEDIA|BAJA",
      "accion": "Acción concreta y específica a tomar",
      "razon": "Por qué esta acción resuelve el problema"
    }}
  ],
  "metricas_sugeridas": [
    "Métrica 1 para monitorear",
    "Métrica 2 para monitorear"
  ]
}}

REGLAS ESTRICTAS:
- Sé ESPECÍFICO, no genérico. Si dice "Cannot read property 'code' of undefined", di eso, no "error de JavaScript".
- Máximo 5 categorías, máximo 5 acciones.
- No repitas el mismo error con diferentes palabras.
- Si no puedes determinar algo, usa "no determinado" en vez de inventar.
- NO incluyas texto fuera del JSON."""

        return prompt
    
    def _call_model_with_retry(self, prompt: str, max_retries: int = 2) -> Dict:
        """Llama al modelo con reintentos y validación JSON"""
        for attempt in range(max_retries):
            try:
                # Llamar al modelo con parámetros optimizados
                response = self.ollama_client.analyze(
                    prompt=prompt,
                    temperature=0.1,  # Baja temperatura para respuestas consistentes
                    max_tokens=2000
                )
                
                # Si la respuesta ya es un dict, retornarla
                if isinstance(response, dict):
                    return response
                
                # Si es string, intentar parsear JSON
                if isinstance(response, str):
                    return self._extract_json(response)
                
                return {"error": "Respuesta inesperada del modelo", "raw": str(response)}
                
            except Exception as e:
                logger.warning(f"Intento {attempt + 1} falló: {e}")
                if attempt == max_retries - 1:
                    return {"error": str(e)}
        
        return {"error": "Máximo de reintentos alcanzado"}
    
    def _extract_json(self, text: str) -> Dict:
        """Extrae JSON de una respuesta de texto"""
        # Intentar parsear directo
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Buscar JSON dentro de bloques de código
        import re
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        # Buscar el primer { ... } balanceado
        try:
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                return json.loads(text[start:end+1])
        except json.JSONDecodeError:
            pass
        
        return {"error": "No se pudo parsear JSON", "raw": text[:500]}
    
    def _validate_and_structure(self, result: Dict, grouped_errors: Dict) -> Dict[str, Any]:
        """Valida y estructura la respuesta del modelo"""
        if "error" in result and "raw" in result:
            return {
                "status": "error_parsing",
                "error": result["error"],
                "raw_response": result.get("raw", "")[:500]
            }
        
        if "error" in result:
            return {"status": "failed", "error": result["error"]}
        
        # Estructura esperada
        structured = {
            "status": "success",
            "resumen_ejecutivo": result.get("resumen_ejecutivo", "No disponible"),
            "severidad_global": result.get("severidad_global", "UNKNOWN"),
            "categorias": result.get("categorias", []),
            "patrones_clave": result.get("patrones_clave", []),
            "acciones_recomendadas": result.get("acciones_recomendadas", []),
            "metricas_sugeridas": result.get("metricas_sugeridas", []),
            "total_grupos_analizados": len(grouped_errors),
        }
        
        return structured
    
    def analyze_with_model(self, errors: List[Dict], model: str, context: Dict = None) -> Dict[str, Any]:
        """Analiza errores con un modelo específico"""
        try:
            # Mismo enfoque pero con modelo específico
            grouped_errors = self._group_errors(errors)
            representative = self._select_representative_errors(grouped_errors, max_total=10)
            prompt = self._build_structured_prompt(representative, context)
            
            response = self.ollama_client.analyze_with_model(
                prompt=prompt,
                model=model,
                temperature=0.1
            )
            
            if isinstance(response, str):
                response = self._extract_json(response)
            
            return self._validate_and_structure(response, grouped_errors)
            
        except Exception as e:
            logger.error(f"Error en análisis con modelo {model}: {str(e)}")
            return {"status": "failed", "error": str(e)}