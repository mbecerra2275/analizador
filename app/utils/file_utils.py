"""
Utilidades para manejo de archivos (lectura tolerante a fallos).

Los logs llegan de Windows, Linux y mainframes con codificaciones mezcladas
(UTF-8, Latin-1, etc.). Estas utilidades priorizan "leer algo útil" sobre
"fallar perfecto": ante un error devuelven None y lo registran en el log,
para que el pipeline pueda mostrar un mensaje claro en vez de crashear.
"""
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class FileUtils:
    """Operaciones de lectura e inspección de archivos (todo estático, sin estado)."""

    @staticmethod
    def read_file(file_path: str, encoding: str = 'utf-8') -> Optional[str]:
        """
        Lee un archivo de texto completo y devuelve su contenido.

        Estrategia de codificación en cascada: primero UTF-8 (el estándar
        actual) y si falla, Latin-1 (acepta cualquier byte, nunca falla por
        caracteres inválidos). En ambos casos errors='ignore' descarta los
        bytes imposibles en vez de abortar la lectura.

        Args:
            file_path: Ruta del archivo a leer.
            encoding: Codificación a intentar primero.

        Returns:
            Contenido como string, o None si el archivo no existe o no se
            puede leer (el motivo queda en el logger).
        """
        path = Path(file_path)

        # Fallo rápido con mensaje claro si la ruta no existe.
        if not path.exists():
            logger.error(f"Archivo no encontrado: {file_path}")
            return None

        try:
            with open(path, 'r', encoding=encoding, errors='ignore') as f:
                return f.read()
        except UnicodeDecodeError:
            # El archivo no es UTF-8 válido (típico de logs Windows antiguos):
            # reintentar con Latin-1, que mapea cada byte a un carácter.
            try:
                with open(path, 'r', encoding='latin-1', errors='ignore') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error leyendo archivo con latin-1: {str(e)}")
                return None
        except Exception as e:
            # Permisos, archivo bloqueado por otro proceso, disco lleno, etc.
            logger.error(f"Error leyendo archivo: {str(e)}")
            return None
    
    @staticmethod
    def read_file_lines(file_path: str, encoding: str = 'utf-8') -> Optional[list]:
        """
        Lee un archivo y lo devuelve como lista de líneas (sin saltos).

        Reutiliza read_file para heredar la tolerancia a codificaciones;
        splitlines() además maneja \\n, \\r\\n y \\r indistintamente.

        Args:
            file_path: Ruta del archivo.
            encoding: Codificación a intentar primero.

        Returns:
            Lista de líneas, o None si el archivo no se pudo leer.
        """
        content = FileUtils.read_file(file_path, encoding)
        if content:
            return content.splitlines()
        return None
    
    @staticmethod
    def get_file_info(file_path: str) -> dict:
        """
        Obtiene metadatos de un archivo para mostrar en la GUI/CLI.

        No lanza excepciones: si el archivo no existe devuelve
        {'exists': False} para que el llamador decida cómo avisar.

        Args:
            file_path: Ruta del archivo.

        Returns:
            Dict con exists, name, size (bytes), size_human ("2.4 MB"),
            extension y modified (timestamp Unix).
        """
        path = Path(file_path)

        if not path.exists():
            return {'exists': False}

        return {
            'exists': True,
            'name': path.name,                                          # Solo el nombre, sin carpetas
            'size': path.stat().st_size,                                # Bytes exactos (para cálculos)
            'size_human': FileUtils._format_size(path.stat().st_size),  # Legible (para mostrar)
            'extension': path.suffix,                                   # ".log", ".txt", ...
            'modified': path.stat().st_mtime                            # Última modificación (Unix timestamp)
        }
    
    @staticmethod
    def _format_size(size: int) -> str:
        """
        Convierte bytes a texto legible ("1536" → "1.5 KB").

        Divide entre 1024 hasta que el valor baje de 1024; si supera GB
        se asume TB (los logs rara vez llegan ahí, pero queda cubierto).
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    @staticmethod
    def is_log_file(file_path: str) -> bool:
        """
        Verifica por extensión si un archivo es analizable (.log o .txt).

        La comparación es case-insensitive para aceptar ".LOG" o ".TXT"
        de sistemas Windows. Solo mira la extensión, no el contenido.
        """
        path = Path(file_path)
        valid_extensions = {'.log', '.txt'}
        return path.suffix.lower() in valid_extensions