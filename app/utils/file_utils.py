"""
Utilidades para manejo de archivos.
"""
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class FileUtils:
    """Utilidades para manejo de archivos."""
    
    @staticmethod
    def read_file(file_path: str, encoding: str = 'utf-8') -> Optional[str]:
        """
        Lee un archivo y devuelve su contenido.
        
        Args:
            file_path: Ruta del archivo
            encoding: Codificación del archivo
            
        Returns:
            Contenido del archivo o None si hay error
        """
        path = Path(file_path)
        
        if not path.exists():
            logger.error(f"Archivo no encontrado: {file_path}")
            return None
        
        try:
            with open(path, 'r', encoding=encoding, errors='ignore') as f:
                return f.read()
        except UnicodeDecodeError:
            # Intentar con otra codificación
            try:
                with open(path, 'r', encoding='latin-1', errors='ignore') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error leyendo archivo con latin-1: {str(e)}")
                return None
        except Exception as e:
            logger.error(f"Error leyendo archivo: {str(e)}")
            return None
    
    @staticmethod
    def read_file_lines(file_path: str, encoding: str = 'utf-8') -> Optional[list]:
        """
        Lee un archivo y devuelve sus líneas.
        
        Args:
            file_path: Ruta del archivo
            encoding: Codificación del archivo
            
        Returns:
            Lista de líneas o None si hay error
        """
        content = FileUtils.read_file(file_path, encoding)
        if content:
            return content.splitlines()
        return None
    
    @staticmethod
    def get_file_info(file_path: str) -> dict:
        """
        Obtiene información de un archivo.
        
        Args:
            file_path: Ruta del archivo
            
        Returns:
            Diccionario con información del archivo
        """
        path = Path(file_path)
        
        if not path.exists():
            return {'exists': False}
        
        return {
            'exists': True,
            'name': path.name,
            'size': path.stat().st_size,
            'size_human': FileUtils._format_size(path.stat().st_size),
            'extension': path.suffix,
            'modified': path.stat().st_mtime
        }
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Formatea el tamaño en bytes a una representación legible."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @staticmethod
    def is_log_file(file_path: str) -> bool:
        """Verifica si un archivo es un archivo de log."""
        path = Path(file_path)
        valid_extensions = {'.log', '.txt'}
        return path.suffix.lower() in valid_extensions