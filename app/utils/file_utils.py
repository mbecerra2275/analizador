# app/utils/file_utils.py
import os
import glob
from typing import List, Optional
from datetime import datetime

def find_log_files(directory: str, pattern: str = "*.log") -> List[str]:
    """Encuentra archivos de log en un directorio"""
    pattern = os.path.join(directory, pattern)
    return glob.glob(pattern)

def get_file_info(filepath: str) -> dict:
    """Obtiene información de un archivo"""
    stats = os.stat(filepath)
    return {
        'filename': os.path.basename(filepath),
        'size': stats.st_size,
        'size_mb': stats.st_size / (1024 * 1024),
        'modified': datetime.fromtimestamp(stats.st_mtime),
        'created': datetime.fromtimestamp(stats.st_ctime)
    }

def ensure_directory(path: str) -> bool:
    """Asegura que un directorio exista"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creando directorio {path}: {e}")
        return False