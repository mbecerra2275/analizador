#!/usr/bin/env python
"""
Script simple para probar la conexión con Ollama.
"""
import sys
import logging
from pathlib import Path

# Configurar logging básico
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Agregar la ruta de la aplicación
sys.path.insert(0, str(Path(__file__).parent))

from app.ai.ollama_client import OllamaClient

def main():
    print("\n" + "="*60)
    print("🧪 PRUEBA DE CONEXIÓN CON OLLAMA")
    print("="*60)
    
    # Crear cliente con configuración mejorada
    client = OllamaClient(
        timeout=45,
        connection_timeout=10,
        max_retries=5
    )
    
    # 1. Diagnóstico
    print("\n🔍 Ejecutando diagnóstico...")
    diagnostic = client.test_connection(verbose=True)
    
    if not diagnostic.is_available:
        print("\n❌ Ollama no está disponible.")
        print("\nPosibles soluciones:")
        print("  1. Ejecuta: ollama serve")
        print("  2. Verifica: curl http://127.0.0.1:11434")
        print("  3. Asegúrate de tener el modelo: ollama pull qwen2.5-coder:1.5b")
        return False
    
    # 2. Prueba de generación
    print("\n" + "="*60)
    print("🧪 Probando generación...")
    print("="*60)
    
    prompt = "Responde 'OK' si estás funcionando correctamente."
    print(f"📝 Prompt: {prompt}")
    
    response = client.generate(prompt, num_predict=10)
    
    if response:
        print(f"✅ Respuesta: {response}")
        print("✅ Prueba exitosa!")
    else:
        print("❌ Falló la generación")
        return False
    
    print("\n" + "="*60)
    print("✅ TODAS LAS PRUEBAS PASARON")
    print("="*60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)