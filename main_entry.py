#!/usr/bin/env python
"""
Entry point para PyInstaller - maneja imports relativos en modo frozen
"""
import sys
import os
from pathlib import Path

# Detectar si estamos corriendo en PyInstaller
if getattr(sys, 'frozen', False):
    # Estamos en PyInstaller - el directorio base es sys._MEIPASS
    BASE_DIR = Path(sys._MEIPASS)
    # Agregar al path para imports
    sys.path.insert(0, str(BASE_DIR))
    # Cambiar directorio de trabajo al directorio del ejecutable
    os.chdir(Path(sys.executable).parent)
else:
    BASE_DIR = Path(__file__).parent

# Ahora importar y ejecutar la app principal
from app.cli import main

if __name__ == "__main__":
    main()