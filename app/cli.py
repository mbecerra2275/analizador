"""
Interfaz de línea de comandos con soporte para GUI.
"""
import argparse
import sys
import logging
from pathlib import Path

from .utils.ollama_checker import OllamaChecker
from .services.analysis_service import AnalysisService
from .config import Config

def setup_logging(verbose: bool = False):
    """Configura el logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def check_ollama_status():
    """Muestra el estado de Ollama."""
    print("\n🔍 Verificando estado de Ollama...")
    
    installed = OllamaChecker.is_installed()
    print(f"  Instalado: {'✅' if installed else '❌'}")
    
    if installed:
        running = OllamaChecker.is_running()
        print(f"  Corriendo: {'✅' if running else '❌'}")
        
        if not running:
            print("  Intentando iniciar...")
            success, msg = OllamaChecker.start_ollama()
            print(f"  {'✅' if success else '❌'} {msg}")

def main():
    """Punto de entrada principal."""
    parser = argparse.ArgumentParser(description="Analizador de Logs con IA")
    parser.add_argument('--file', '-f', help='Archivo de logs a analizar')
    parser.add_argument('--gui', '-g', action='store_true', help='Abrir interfaz gráfica')
    parser.add_argument('--verbose', '-v', action='store_true', help='Modo verbose')
    parser.add_argument('--check-ollama', action='store_true', help='Verificar estado de Ollama')
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    if args.check_ollama:
        check_ollama_status()
        return
    
    if args.gui:
        # Abrir GUI
        try:
            from .gui.main_window import MainWindow
            app = MainWindow()
            app.run()
            return
        except ImportError as e:
            print(f"❌ Error cargando GUI: {e}")
            print("Ejecutando en modo CLI...")
            # Continuar a modo CLI
    
    # Modo CLI
    file_path = args.file
    if not file_path:
        file_path = input("📁 Ruta del archivo de logs: ").strip()
        if not file_path:
            print("❌ No se especificó archivo")
            sys.exit(1)
    
    if not Path(file_path).exists():
        print(f"❌ Archivo no encontrado: {file_path}")
        sys.exit(1)
    
    # Verificar Ollama
    check_ollama_status()
    
    # Ejecutar análisis
    print(f"\n📊 Analizando: {file_path}")
    config = Config()
    service = AnalysisService(config)
    report = service.analyze_file(file_path)
    
    print(f"\n✅ Análisis completado")
    print(f"📄 Reporte: {report.get('report_path', 'No generado')}")
    print(f"📊 Logs: {report.get('total_logs', 0):,}")
    print(f"🔄 Transacciones: {report.get('total_groups', 0):,}")
    print(f"⚠️ Errores: {len(report.get('errors', []))}")
    
    ai_status = report.get('ai_analysis', {}).get('status', 'No disponible')
    print(f"🤖 IA: {ai_status}")

if __name__ == "__main__":
    main()