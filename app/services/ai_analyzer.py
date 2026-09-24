"""
Analizador con IA para errores de logs.

Orquesta las dos piezas de app/ai/: PromptBuilder (convierte errores
estructurados en un prompt optimizado) y OllamaClient (habla con el
servidor Ollama local). Si la IA no responde, degrada con gracia a un
análisis básico sin IA para no bloquear el reporte.
"""
import logging
from typing import Dict, Any, List, Optional

from ..ai.ollama_client import OllamaClient
from ..ai.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """Analizador de errores usando IA local (Ollama)."""

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el analizador IA.

        Args:
            config: Diccionario con configuración de Ollama (sale de
                Config.to_dict(): url, modelo, timeouts, reintentos...).
                Los .get() con default permiten instanciarlo incluso con
                un config parcial sin que falle.
        """
        self.config = config
        self.client = OllamaClient(
            base_url=config.get('ollama_url', 'http://127.0.0.1:11434'),
            timeout=config.get('ollama_timeout', 120),
            connection_timeout=config.get('ollama_connection_timeout', 15),
            max_retries=config.get('ollama_max_retries', 3),
            retry_delay=config.get('ollama_retry_delay', 3),
            backoff_multiplier=config.get('ollama_backoff_multiplier', 2)
        )
        self.prompt_builder = PromptBuilder()
        # Cache del estado de Ollama: el chequeo hace red, así que se hace
        # una sola vez por instancia en vez de en cada llamada.
        self._available = None

    @property
    def is_available(self) -> bool:
        """
        Indica si Ollama responde (con caché).

        Es property para que el llamador lo use como atributo
        (analyzer.is_available) sin preocuparse del chequeo de red.
        """
        if self._available is None:
            self._available = self.client.is_available()
        return self._available

    def analyze_errors(
        self,
        errors: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analiza una lista de errores con IA y devuelve diagnóstico en texto.

        Cascada de degradación (de mejor a peor caso):
        1. success → la IA respondió con el análisis completo.
        2. partial → la IA respondió vacío: se usa análisis básico local.
        3. offline → Ollama no corre: se avisa y el reporte sigue sin IA.
        4. error → excepción inesperada: se registra y se devuelve el error.

        Args:
            errors: Lista de errores ya deduplicados (de AnalysisService).
            context: Contexto adicional (nº grupos, ratio deduplicación...).

        Returns:
            Dict con status ('success'|'partial'|'offline'|'error'),
            analysis (texto) y errors_analyzed (nº procesado).
        """
        try:
            # Caso trivial: sin errores no hay nada que preguntar a la IA.
            if not errors:
                return {
                    'status': 'success',
                    'analysis': '✅ No se encontraron errores. Todo funciona correctamente.',
                    'errors_analyzed': 0
                }

            # Sin servidor no se puede generar: se avisa con estado 'offline'
            # para que la GUI muestre modo degradado en vez de un crash.
            if not self.is_available:
                return {
                    'status': 'offline',
                    'analysis': '⚠️ Análisis IA no disponible - Ollama no está corriendo o no responde',
                    'errors_analyzed': len(errors)
                }

            # Paso 1: convertir errores estructurados en prompt optimizado
            # (limitado en nº de errores y longitud para no saturar el modelo).
            prompt = self.prompt_builder.build_error_analysis_prompt(errors, context)

            # Paso 2: pedir la generación al servidor Ollama local.
            # temperature baja (0.3) = respuestas deterministas y técnicas.
            response = self.client.generate(
                prompt=prompt,
                model=self.config.get('ollama_model'),
                temperature=self.config.get('ollama_temperature', 0.3),
                num_predict=self.config.get('ollama_num_predict', 300),
                top_p=self.config.get('ollama_top_p', 0.9)
            )

            if response:
                return {
                    'status': 'success',
                    'analysis': response.strip(),
                    'errors_analyzed': len(errors)
                }
            else:
                # El servidor respondió pero sin texto útil: degradar a
                # análisis local para no dejar el reporte vacío.
                logger.warning("Respuesta vacía de Ollama")
                return {
                    'status': 'partial',
                    'analysis': self._generate_fallback_analysis(errors),
                    'errors_analyzed': len(errors)
                }

        except Exception as e:
            logger.error(f"Error en análisis IA: {str(e)}")
            return {
                'status': 'error',
                'analysis': f'⚠️ Error en análisis IA: {str(e)}',
                'errors_analyzed': len(errors)
            }

    def _generate_fallback_analysis(self, errors: List[Dict[str, Any]]) -> str:
        """
        Genera un resumen legible sin IA (plan B cuando Ollama falla).

        Lista los 10 primeros grupos con su correlation-id, nº de errores
        y primer mensaje truncado a 150 chars, para que el reporte tenga
        al menos un inventario útil aunque no haya diagnóstico.
        """
        if not errors:
            return "✅ No se encontraron errores."

        analysis = []
        analysis.append(f"⚠️ Se encontraron {len(errors)} grupos con errores:")

        # Solo los 10 primeros: más sería ruido en un resumen sin IA.
        for i, error in enumerate(errors[:10], 1):
            corr_id = error.get('correlation_id', 'N/A')
            count = error.get('error_count', 0)
            messages = error.get('messages', [])

            analysis.append(f"\n{i}. Correlation ID: {corr_id}")
            analysis.append(f"   Errores: {count}")

            if messages:
                first_msg = messages[0]
                # Truncar para que cada fila quepa en una línea del reporte.
                if len(first_msg) > 150:
                    first_msg = first_msg[:150] + "..."
                analysis.append(f"   Mensaje: {first_msg}")

        if len(errors) > 10:
            analysis.append(f"\n... y {len(errors) - 10} errores más")

        analysis.append("\n💡 Recomendación: Revisar los logs para más detalles")

        return "\n".join(analysis)

    def list_models(self) -> List[str]:
        """Delega al cliente: lista los modelos descargados en Ollama."""
        return self.client.list_models()

    def test_connection(self) -> Dict[str, Any]:
        """Delega al cliente: diagnóstico completo de conexión (verbose)."""
        return self.client.test_connection(verbose=True)