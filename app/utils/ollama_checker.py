"""
Utilidades para verificar y gestionar Ollama.
"""
import subprocess
import sys
import time
import logging
import socket
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class OllamaChecker:
    """Verificador y gestor de Ollama."""
    
    @staticmethod
    def is_installed() -> bool:
        """Verifica si Ollama está instalado."""
        try:
            subprocess.run(['ollama', '--version'], 
                          capture_output=True, 
                          check=True,
                          timeout=5)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    @staticmethod
    def is_running(host: str = '127.0.0.1', port: int = 11434) -> bool:
        """Verifica si Ollama está corriendo."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    @staticmethod
    def start_ollama(background: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Intenta iniciar Ollama.
        
        Returns:
            (success, message)
        """
        if not OllamaChecker.is_installed():
            return False, "Ollama no está instalado en el sistema"
        
        if OllamaChecker.is_running():
            return True, "Ollama ya está corriendo"
        
        try:
            if sys.platform == 'win32':
                # Windows
                subprocess.Popen(
                    ['ollama', 'serve'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if background else 0
                )
            else:
                # Linux/Mac
                subprocess.Popen(
                    ['ollama', 'serve'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=background
                )
            
            # Esperar a que inicie
            for _ in range(10):
                time.sleep(1)
                if OllamaChecker.is_running():
                    return True, "Ollama iniciado correctamente"
            
            return False, "Ollama no inició después de 10 segundos"
            
        except Exception as e:
            return False, f"Error iniciando Ollama: {str(e)}"
    
    @staticmethod
    def ensure_model_available(model: str) -> Tuple[bool, Optional[str]]:
        """
        Verifica que el modelo esté disponible, lo descarga si no.
        """
        if not OllamaChecker.is_running():
            return False, "Ollama no está corriendo"
        
        try:
            # Listar modelos
            import requests
            response = requests.get('http://127.0.0.1:11434/api/tags', timeout=5)
            if response.status_code == 200:
                models = [m['name'] for m in response.json().get('models', [])]
                if model in models:
                    return True, f"Modelo {model} disponible"
            
            # Descargar modelo
            logger.info(f"Descargando modelo {model}...")
            subprocess.run(['ollama', 'pull', model], check=True, timeout=300)
            return True, f"Modelo {model} descargado"
            
        except Exception as e:
            return False, f"Error con el modelo: {str(e)}"