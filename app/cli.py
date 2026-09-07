# app/cli.py
import argparse
import sys
import os
from pathlib import Path
from tkinter import Tk, filedialog
from app.services.analysis_service import AnalysisService
from app.config import load_config

def seleccionar_archivo():
    """Abre un diálogo para seleccionar archivo manualmente"""
    try:
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        archivo = filedialog.askopenfilename(
            title="Selecciona el archivo de log",
            filetypes=[
                ("Archivos de log", "*.log"),
                ("Archivos de texto", "*.txt"),
                ("Todos los archivos", "*.*")
            ],
            initialdir=os.path.expanduser("~/Downloads")
        )
        root.destroy()
        
        return archivo if archivo else None
    except:
        print("⚠️  No se pudo abrir el selector de archivos")
        return None

def main():
    parser = argparse.ArgumentParser(
        description="Herramienta de análisis de logs con IA",
        epilog="Ejemplo: python -m app.cli --file logs/error.log"
    )
    
    parser.add_argument(
        '--file', '-f',
        help='Ruta al archivo de log a analizar'
    )
    
    parser.add_argument(
        '--gui', '-g',
        action='store_true',
        help='Abre un selector gráfico para elegir el archivo'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Directorio de salida para reportes'
    )
    
    parser.add_argument(
        '--no-ai',
        action='store_true',
        help='Deshabilita el análisis con IA'
    )
    
    parser.add_argument(
        '--model',
        default='qwen2.5-coder:1.5b',
        help='Modelo de Ollama a utilizar'
    )
    
    parser.add_argument(
        '--config',
        help='Archivo de configuración YAML'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Muestra información detallada'
    )
    
    args = parser.parse_args()
    
    # Determinar el archivo
    log_file = args.file
    
    if args.gui or not log_file:
        print("📂 Selecciona el archivo de log...")
        log_file = seleccionar_archivo()
        if not log_file:
            print("❌ No se seleccionó ningún archivo")
            sys.exit(1)
        print(f"✅ Archivo seleccionado: {log_file}")
    
    if not os.path.exists(log_file):
        print(f"❌ Error: El archivo '{log_file}' no existe")
        sys.exit(1)
    
    config = load_config(args.config) if args.config else {}
    
    config.update({
        'output_dir': args.output or config.get('output_dir', 'output/reports/'),
        'ai_model': args.model,
        'use_ai': not args.no_ai,
        'verbose': args.verbose
    })
    
    print("🚀 Iniciando análisis de logs...")
    print("=" * 50)
    
    service = AnalysisService(config)
    result = service.analyze_log_file(log_file, use_ai=not args.no_ai)
    
    print("=" * 50)
    print("📊 Resumen final:")
    print(f"   Total transacciones: {result['statistics']['total_transactions']}")
    print(f"   Tasa de éxito: {result['statistics']['success_rate']:.1f}%")
    print(f"   Errores reales: {len(result['true_errors'])}")
    print(f"   Falsos positivos: {len(result['false_positives'])}")
    
    if result.get('recommendations'):
        print("\n💡 Recomendaciones principales:")
        for rec in result['recommendations'][:3]:
            print(f"   • {rec}")
    
    print("\n✅ Análisis completado")

if __name__ == '__main__':
    main()