"""
Analizador con IA para errores de logs.
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
            config: Diccionario con configuración de Ollama
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
        self._available = None

    @property
    def is_available(self) -> bool:
        """Verifica si Ollama está disponible (con cache)."""
        if self._available is None:
            self._available = self.client.is_available()
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
            context: Contexto adicional (total_groups, etc.)

        Returns:
            Diccionario con resultado del análisis
        """
        try:
            if not errors:
                return {
                    'status': 'success',
                    'analysis': '✅ No se encontraron errores. Todo funciona correctamente.',
                    'errors_analyzed': 0
                }

            if not self.is_available:
                return {
                    'status': 'offline',
                    'analysis': '⚠️ Análisis IA no disponible - Ollama no está corriendo o no responde',
                    'errors_analyzed': len(errors)
                }

            # Construir prompt optimizado
            prompt = self.prompt_builder.build_error_analysis_prompt(errors, context)

            # Generar respuesta
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
        """Genera análisis básico sin IA."""
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

    def list_models(self) -> List[str]:
        """Lista modelos disponibles en Ollama."""
        return self.client.list_models()

    def test_connection(self) -> Dict[str, Any]:
        """Prueba la conexión con Ollama."""
        return self.client.test_connection(verbose=True)