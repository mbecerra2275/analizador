"""
Interfaz de línea de comandos con soporte para GUI.
"""
import argparse        # Parseo de argumentos de la CLI
import sys             # Salida del programa con código de error
import logging         # Logging interno de la aplicación
from pathlib import Path  # Manejo portable de rutas

from .utils.ollama_checker import OllamaChecker         # Comprueba/arranca Ollama
from .services.analysis_service import AnalysisService  # Servicio de análisis
from .config import Config                              # Configuración global


def setup_logging(verbose: bool = False):
    """Configura el logging."""
    # Nivel DEBUG si verbose, si no INFO
    level = logging.DEBUG if verbose else logging.INFO
    # Formato estándar de los mensajes de log
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def check_ollama_status():
    """Muestra el estado de Ollama."""
    print("\n🔍 Verificando estado de Ollama...")

    # ¿Está instalado?
    installed = OllamaChecker.is_installed()
    print(f"  Instalado: {'✅' if installed else '❌'}")

    if installed:
        # ¿Está corriendo?
        running = OllamaChecker.is_running()
        print(f"  Corriendo: {'✅' if running else '❌'}")

        if not running:
            # Intentar arrancarlo
            print("  Intentando iniciar...")
            success, msg = OllamaChecker.start_ollama()
            print(f"  {'✅' if success else '❌'} {msg}")


def main():
    """Punto de entrada principal."""
    # Definición de argumentos de la CLI
    parser = argparse.ArgumentParser(description="Analizador de Logs con IA")
    parser.add_argument('--file', '-f', help='Archivo de logs a analizar')
    parser.add_argument('--gui', '-g', action='store_true', help='Abrir interfaz gráfica')
    parser.add_argument('--verbose', '-v', action='store_true', help='Modo verbose')
    parser.add_argument('--check-ollama', action='store_true', help='Verificar estado de Ollama')

    args = parser.parse_args()

    # Configurar logging según verbose
    setup_logging(args.verbose)

    # Modo: solo verificar Ollama
    if args.check_ollama:
        check_ollama_status()
        return

    # Modo: GUI (con fallback a CLI si falla el import)
    if args.gui:
        try:
            from .gui.main_window import MainWindow
            app = MainWindow()
            app.run()
            return
        except ImportError as e:
            print(f"❌ Error cargando GUI: {e}")
            print("Ejecutando en modo CLI...")
            # Sin return: continúa en modo CLI

    # Modo: CLI
    file_path = args.file

    # Si no se pasó --file, pedirlo por consola
    if not file_path:
        file_path = input("📁 Ruta del archivo de logs: ").strip()
        if not file_path:
            print("❌ No se especificó archivo")
            sys.exit(1)

    # Validar que el archivo exista
    if not Path(file_path).exists():
        print(f"❌ Archivo no encontrado: {file_path}")
        sys.exit(1)

    # Verificar Ollama antes de analizar
    check_ollama_status()

    # Ejecutar análisis
    print(f"\n📊 Analizando: {file_path}")
    config = Config()
    service = AnalysisService(config)
    report = service.analyze_file(file_path)

    # Resumen final por consola
    print(f"\n✅ Análisis completado")
    print(f"📄 Reporte: {report.get('report_path', 'No generado')}")
    print(f"📊 Logs: {report.get('total_logs', 0):,}")
    print(f"🔄 Transacciones: {report.get('total_groups', 0):,}")
    print(f"⚠️ Errores: {len(report.get('errors', []))}")

    # Estado del análisis con IA
    ai_status = report.get('ai_analysis', {}).get('status', 'No disponible')
    print(f"🤖 IA: {ai_status}")


# Solo ejecuta main() si se corre el archivo directamente
if __name__ == "__main__":
    main()