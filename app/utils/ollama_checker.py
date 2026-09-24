"""
Utilidades para verificar y gestionar Ollama (el motor de IA local).

Antes de pedir un análisis a la IA hay que responder 3 preguntas en orden:
1. ¿Está Ollama instalado? (existe el binario `ollama`)
2. ¿Está el servidor corriendo? (escucha en 127.0.0.1:11434)
3. ¿Está el modelo descargado? (ej: qwen2.5-coder:1.5b)

Esta clase responde las 3 y, si hace falta, intenta arrancar el servidor
o descargar el modelo automáticamente.
"""
import subprocess
import sys
import time
import logging
import socket
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class OllamaChecker:
    """Verificador y gestor del ciclo de vida de Ollama (todo estático, sin estado)."""

    @staticmethod
    def is_installed() -> bool:
        """
        Verifica si el binario `ollama` existe en el PATH.

        Se usa `ollama --version` (comando inocuo y rápido) en vez de buscar
        el ejecutable a mano, así funciona igual en Windows, Linux y Mac.
        """
        try:
            subprocess.run(['ollama', '--version'],
                          capture_output=True,   # No ensuciar la consola del usuario
                          check=True,            # Lanza excepción si el exit code != 0
                          timeout=5)             # No bloquear si el binario se cuelga
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            # CalledProcessError: el binario existe pero falló;
            # FileNotFoundError: no existe en el PATH;
            # TimeoutExpired: se quedó colgado.
            return False

    @staticmethod
    def is_running(host: str = '127.0.0.1', port: int = 11434) -> bool:
        """
        Verifica si el servidor Ollama acepta conexiones TCP.

        Se hace un connect TCP directo al puerto en vez de una petición HTTP
        porque es más rápido (ms) y no requiere parsear respuestas: si el
        puerto responde, el servidor está arriba.

        Args:
            host: Interfaz donde escucha Ollama (por defecto solo localhost).
            port: Puerto por defecto de Ollama.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)  # No esperar más de 2s si no hay servidor
            # connect_ex devuelve 0 si conecta, o el código de error si no.
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            # Cualquier error de red se trata como "no corriendo".
            return False
    
    @staticmethod
    def start_ollama(background: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Intenta arrancar el servidor Ollama (`ollama serve`).

        Flujo: si no está instalado → error; si ya corre → éxito inmediato;
        si no, lo lanza como proceso hijo en segundo plano y espera hasta
        10 segundos a que el puerto 11434 empiece a responder.

        Args:
            background: Si True, el servidor queda en segundo plano sin
                ventana de consola (Windows) o en su propia sesión (Unix).

        Returns:
            Tupla (success, message) con el resultado legible para la GUI/CLI.
        """
        # Sin binario no hay nada que arrancar: se avisa con mensaje claro.
        if not OllamaChecker.is_installed():
            return False, "Ollama no está instalado en el sistema"

        # Idempotente: si ya responde el puerto, no se lanza otro proceso.
        if OllamaChecker.is_running():
            return True, "Ollama ya está corriendo"

        try:
            if sys.platform == 'win32':
                # En Windows CREATE_NO_WINDOW evita que aparezca una consola
                # negra flotante al lanzar el servidor en segundo plano.
                subprocess.Popen(
                    ['ollama', 'serve'],
                    stdout=subprocess.DEVNULL,  # Silenciar logs del servidor
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if background else 0
                )
            else:
                # En Linux/Mac start_new_session lo desvincula de la terminal
                # para que sobreviva si se cierra la consola que lo lanzó.
                subprocess.Popen(
                    ['ollama', 'serve'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=background
                )

            # Polling: el servidor tarda unos segundos en abrir el puerto,
            # así que se reintenta cada segundo hasta 10 veces.
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
        Verifica que el modelo IA esté descargado; si no, lo descarga.

        Primero consulta /api/tags (lista de modelos locales). Solo si el
        modelo no aparece se ejecuta `ollama pull`, que puede tardar minutos
        (los modelos pesan GBs), de ahí el timeout generoso de 300s.

        Args:
            model: Nombre del modelo, ej: "qwen2.5-coder:1.5b".

        Returns:
            Tupla (success, message) con el resultado legible.
        """
        # Sin servidor no se puede ni listar ni descargar modelos.
        if not OllamaChecker.is_running():
            return False, "Ollama no está corriendo"

        try:
            # Paso 1: listar modelos ya descargados en local.
            import requests  # Import diferido: solo se necesita en este método
            response = requests.get('http://127.0.0.1:11434/api/tags', timeout=5)
            if response.status_code == 200:
                models = [m['name'] for m in response.json().get('models', [])]
                if model in models:
                    return True, f"Modelo {model} disponible"

            # Paso 2: el modelo no está → descargarlo (operación larga).
            logger.info(f"Descargando modelo {model}...")
            subprocess.run(['ollama', 'pull', model], check=True, timeout=300)
            return True, f"Modelo {model} descargado"

        except Exception as e:
            return False, f"Error con el modelo: {str(e)}"