"""
Cliente para Ollama con timeouts configurables - VERSIÓN MEJORADA.
"""
import requests
import socket
import time
import logging
from typing import Optional, Dict, Any, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ConnectionDiagnostic:
    """Resultado del diagnóstico de conexión."""
    socket_ok: bool = False
    requests_ok: bool = False
    ollama_ok: bool = False
    models_available: List[str] = field(default_factory=list)
    details: List[str] = field(default_factory=list)
    is_available: bool = False
    
    def get(self, key, default=None):
        if hasattr(self, key):
            return getattr(self, key)
        return default
    
    def __getitem__(self, key):
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

class OllamaClient:
    """Cliente para Ollama con timeouts optimizados."""
    
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        timeout: int = 120,  # Aumentado a 120 segundos
        connection_timeout: int = 15,
        max_retries: int = 3,  # Reducido a 3 para no esperar tanto
        retry_delay: int = 3,
        backoff_multiplier: int = 2
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.connection_timeout = connection_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_multiplier = backoff_multiplier
        
        self.session = self._create_session()
        self._diagnostic = None
        
    def _create_session(self) -> requests.Session:
        """Crea una sesión HTTP con configuración optimizada."""
        session = requests.Session()
        
        session.trust_env = False
        session.proxies = {"http": None, "https": None}
        
        session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'LogAnalyzer/2.0'
        })
        
        # Timeouts más largos para la sesión
        session.timeout = (self.connection_timeout, self.timeout)
        
        return session
    
    def test_connection(self, verbose: bool = False) -> ConnectionDiagnostic:
        """Prueba rápida de conexión."""
        diagnostic = ConnectionDiagnostic()
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex(('127.0.0.1', 11434))
            sock.close()
            diagnostic.socket_ok = result == 0
            if diagnostic.socket_ok:
                diagnostic.details.append('✅ Socket: OK')
            else:
                diagnostic.details.append('❌ Socket: No disponible')
        except Exception as e:
            diagnostic.details.append(f'❌ Socket: {str(e)}')
        
        if diagnostic.socket_ok:
            try:
                resp = self.session.get(self.base_url, timeout=5)
                diagnostic.requests_ok = resp.status_code == 200
                if diagnostic.requests_ok:
                    diagnostic.details.append('✅ HTTP: OK')
            except Exception as e:
                diagnostic.details.append(f'❌ HTTP: {str(e)}')
        
        if diagnostic.requests_ok:
            try:
                resp = self.session.get(f"{self.base_url}/api/tags", timeout=5)
                if resp.status_code == 200:
                    models = resp.json().get('models', [])
                    diagnostic.models_available = [m.get('name', '') for m in models]
                    diagnostic.details.append(f'✅ Modelos: {len(models)}')
                    if models:
                        diagnostic.ollama_ok = True
            except Exception as e:
                diagnostic.details.append(f'⚠️ API tags: {str(e)}')
        
        diagnostic.is_available = diagnostic.ollama_ok
        
        if verbose:
            print("\n🔍 Diagnóstico de Ollama:")
            for detail in diagnostic.details:
                print(f"  {detail}")
            print(f"\n📊 Disponible: {'✅ Sí' if diagnostic.is_available else '❌ No'}")
        
        self._diagnostic = diagnostic
        return diagnostic
    
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        num_predict: Optional[int] = None,
        top_p: Optional[float] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Genera texto usando Ollama con timeout extendido.
        """
        # Verificar disponibilidad
        if not self._diagnostic or not self._diagnostic.is_available:
            self.test_connection()
            if not self._diagnostic.is_available:
                logger.error("❌ Ollama no disponible.")
                return None
        
        model = model or self._get_default_model()
        
        # Optimizar parámetros para generación más rápida
        temperature = temperature or 0.3
        num_predict = num_predict or 300  # Reducido de 500 a 300
        top_p = top_p or 0.9
        
        # Si el prompt es muy largo, truncarlo
        if len(prompt) > 4000:
            logger.warning(f"Prompt largo ({len(prompt)} chars), truncando...")
            prompt = prompt[:4000] + "\n...[continuación truncada]"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
                "top_p": top_p,
                "repeat_penalty": 1.1,
                "stop": ["\n\n\n"]  # Parar después de 3 saltos de línea
            }
        }
        
        last_error = None
        for attempt in range(self.max_retries):
            # Timeout progresivo
            timeout = self.timeout * (1 + (attempt * 0.3))
            delay = self.retry_delay * (self.backoff_multiplier ** attempt)
            
            try:
                logger.info(f"Intento {attempt + 1}/{self.max_retries} - Timeout: {timeout:.0f}s")
                
                response = self.session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    result = response.json().get('response', '')
                    if result:
                        logger.info(f"✅ Generación exitosa ({len(result)} caracteres)")
                        return result
                    else:
                        logger.warning("⚠️ Respuesta vacía")
                        last_error = "Respuesta vacía"
                else:
                    logger.warning(f"⚠️ Status {response.status_code}")
                    last_error = f"Status {response.status_code}"
                    
            except requests.exceptions.Timeout:
                logger.warning(f"⏱️ Intento {attempt + 1}: Timeout después de {timeout:.0f}s")
                last_error = "Timeout"
                if attempt < self.max_retries - 1:
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"💥 Intento {attempt + 1}: {str(e)}")
                last_error = str(e)
                if attempt < self.max_retries - 1:
                    time.sleep(delay)
        
        logger.error(f"❌ Todos los intentos fallaron. Último error: {last_error}")
        return None
    
    def _get_default_model(self) -> str:
        """Obtiene el modelo por defecto más rápido."""
        if self._diagnostic and self._diagnostic.models_available:
            # Priorizar modelos más pequeños y rápidos
            fast_models = ['tinyllama', 'phi3', 'qwen2.5-coder:1.5b']
            for fast_model in fast_models:
                for model in self._diagnostic.models_available:
                    if fast_model in model:
                        return model
            return self._diagnostic.models_available[0]
        return "qwen2.5-coder:1.5b"
    
    def list_models(self) -> List[str]:
        if not self._diagnostic or not self._diagnostic.is_available:
            self.test_connection()
        return self._diagnostic.models_available if self._diagnostic else []
    
    def is_available(self) -> bool:
        if not self._diagnostic:
            self.test_connection()
        return self._diagnostic.is_available if self._diagnostic else False