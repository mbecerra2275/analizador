#!/usr/bin/env python
"""
Script para compilar Log Analyzer como ejecutable standalone (.exe)
Uso: python build_exe.py
"""
import PyInstaller.__main__
import os
import sys
from pathlib import Path

# Directorio raíz del proyecto
ROOT = Path(__file__).parent
APP_DIR = ROOT / "app"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"

# Limpiar builds previos
import shutil
for d in [DIST_DIR, BUILD_DIR]:
    if d.exists():
        shutil.rmtree(d)

# Configuración de PyInstaller
PyInstaller.__main__.run([
    # Entrada principal (manejador de frozen)
    str(ROOT / "main_entry.py"),
    
    # Nombre del ejecutable
    '--name=LogAnalyzer',
    
    # Un solo archivo
    '--onefile',
    
    # Modo ventana (sin consola) - usa --console para debug
    '--windowed',
    
    # Icono (opcional - crea uno simple si no existe)
    '--icon=NONE',
    
    # Incluir paquete app completo
    f'--add-data={APP_DIR}{os.pathsep}app',
    
    # Imports ocultos necesarios
    '--hidden-import=yaml',
    '--hidden-import=tkinter',
    '--hidden-import=tkinter.ttk',
    '--hidden-import=tkinter.filedialog',
    '--hidden-import=tkinter.messagebox',
    '--hidden-import=tkinter.scrolledtext',
    '--hidden-import=requests',
    '--hidden-import=colorama',
    '--hidden-import=dotenv',
    '--hidden-import=dataclasses_json',
    '--hidden-import=typing_extensions',
    
    # Módulos de la app
    '--hidden-import=app.config',
    '--hidden-import=app.core.log_parser',
    '--hidden-import=app.core.correlation_analyzer',
    '--hidden-import=app.core.smart_filter',
    '--hidden-import=app.core.log_splitter',
    '--hidden-import=app.services.analysis_service',
    '--hidden-import=app.services.ai_analyzer',
    '--hidden-import=app.ai.ollama_client',
    '--hidden-import=app.ai.prompt_builder',
    '--hidden-import=app.reporters.markdown_reporter',
    '--hidden-import=app.utils.file_utils',
    '--hidden-import=app.utils.ollama_checker',
    '--hidden-import=app.models.log_entry',
    '--hidden-import=app.models.correlation_group',
    '--hidden-import=app.models.error_report',
    '--hidden-import=app.gui.main_window',
    
    # Directorios de salida
    f'--distpath={DIST_DIR}',
    f'--workpath={BUILD_DIR}',
    f'--specpath={ROOT}',
    
    # Limpieza
    '--clean',
    '--noconfirm',
    
    # Optimización
    '--strip',
    '--noupx',  # UPX puede causar falsos positivos en antivirus
])

print(f"\n✅ Ejecutable generado en: {DIST_DIR / 'LogAnalyzer.exe'}")
print(f"Tamaño: {(DIST_DIR / 'LogAnalyzer.exe').stat().st_size / (1024*1024):.1f} MB")