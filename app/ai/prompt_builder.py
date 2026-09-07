# app/ai/prompt_builder.py
from typing import List, Dict, Optional
from ..models.log_entry import LogEntry

MAX_ERRORS_IN_SUMMARY = 8
MAX_STACK_TRACE_CHARS = 400


class PromptBuilder:
    """Construye prompts optimizados para diferentes contextos"""

    @staticmethod
    def _safe_attr(entry, attr, default="N/A"):
        """Acceso defensivo a atributos de LogEntry que podrían no venir seteados."""
        value = getattr(entry, attr, default)
        return value if value not in (None, "") else default

    @staticmethod
    def build_summary_prompt(errors: List[Dict]) -> str:
        """Construye prompt para resumen ejecutivo"""
        if not errors:
            return "No hay errores para analizar."

        # Instrucciones PRIMERO: si el prompt se trunca (ej. límite de 1500
        # caracteres en OllamaClient.analyze), el modelo igual sabe qué se le pide.
        instructions = """Analiza el siguiente resumen de errores y genera un diagnóstico ejecutivo.

Proporciona:
1. El problema más crítico
2. Impacto potencial
3. Recomendación inicial
4. Urgencia de la acción

Errores detectados:
"""

        # Limitar cantidad de errores (no solo caracteres) para no perder
        # las instrucciones ni cortar un error a la mitad.
        limited_errors = errors[:MAX_ERRORS_IN_SUMMARY]
        error_summary = []
        for error in limited_errors:
            entry = error['entry']
            severity = error.get('severity', 'Unknown')
            error_type = error.get('type', 'Unknown')
            message = PromptBuilder._safe_attr(entry, 'message', '')[:100]
            error_summary.append(f"- [{severity}] {error_type}: {message}")

        remaining = len(errors) - len(limited_errors)
        if remaining > 0:
            error_summary.append(f"... y {remaining} error(es) más no mostrados.")

        return instructions + chr(10).join(error_summary)

    @staticmethod
    def build_root_cause_prompt(error: Dict) -> str:
        """Construye prompt para análisis de causa raíz"""
        entry = error['entry']
        severity = error.get('severity', 'Unknown')

        message = PromptBuilder._safe_attr(entry, 'message', 'Sin mensaje')
        correlation_id = PromptBuilder._safe_attr(entry, 'correlation_id')
        service = PromptBuilder._safe_attr(entry, 'service')
        class_name = PromptBuilder._safe_attr(entry, 'class_name')
        stack_trace = PromptBuilder._safe_attr(entry, 'stack_trace', 'No disponible')
        if stack_trace != 'No disponible':
            stack_trace = stack_trace[:MAX_STACK_TRACE_CHARS]

        return f"""Analiza este error y determina:
1. Causa raíz probable
2. Por qué ocurrió en este contexto
3. Cómo solucionarlo
4. Cómo prevenir futuras ocurrencias

## Error Crítico
**Tipo:** {error.get('type', 'Unknown')}
**Severidad:** {severity}
**Mensaje:** {message}
**Correlation ID:** {correlation_id}
**Servicio:** {service}
**Clase:** {class_name}
**Stack Trace:** {stack_trace}
"""

    @staticmethod
    def build_pattern_analysis_prompt(errors: List[Dict]) -> str:
        """Construye prompt para análisis de patrones"""
        if not errors:
            return "No hay errores para analizar."

        error_types = {}
        for error in errors:
            error_type = error.get('type', 'Unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1

        # Ordenar por frecuencia descendente: si el prompt se trunca,
        # los patrones más relevantes van primero.
        sorted_types = sorted(error_types.items(), key=lambda x: x[1], reverse=True)
        pattern_summary = [f"- {error_type}: {count} ocurrencias" for error_type, count in sorted_types]

        return f"""Analiza estos patrones y determina:
1. Si existe un problema sistémico
2. Relaciones entre diferentes tipos de errores
3. Recomendaciones para abordar patrones recurrentes

## Patrones de Errores Detectados
{chr(10).join(pattern_summary)}
"""