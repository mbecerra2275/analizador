# diagnostic.py
import os
import sys
import requests
import socket
import subprocess

print("=== DIAGNÓSTICO OLLAMA ===\n")

# 1. Verificar variables de entorno
print("1. Variables de entorno relevantes:")
proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY', 'http_proxy', 'https_proxy', 'no_proxy']
for var in proxy_vars:
    val = os.environ.get(var)
    print(f"   {var} = {val if val else 'No definida'}")

# 2. Verificar puerto con socket
print("\n2. Verificación de puerto con socket:")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 11434))
    if result == 0:
        print("   ✅ Puerto 11434 abierto")
    else:
        print(f"   ❌ Puerto 11434 cerrado (código: {result})")
    sock.close()
except Exception as e:
    print(f"   ❌ Error: {e}")

# 3. Probar requests con diferentes configuraciones
print("\n3. Prueba de requests:")
try:
    # Sin timeout
    r = requests.get('http://127.0.0.1:11434', timeout=10)
    print(f"   ✅ GET exitoso: {r.status_code}")
    print(f"   Response: {r.text[:100]}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# 4. Probar /api/generate (más relevante)
print("\n4. Prueba de API generate:")
try:
    payload = {
        "model": "qwen2.5-coder:1.5b",
        "prompt": "Hola",
        "stream": False
    }
    r = requests.post('http://127.0.0.1:11434/api/generate', 
                      json=payload, 
                      timeout=30)
    print(f"   ✅ API respondió: {r.status_code}")
    print(f"   Response: {r.json().get('response', '')[:50]}...")
except Exception as e:
    print(f"   ❌ Error: {e}")

# 5. Información del entorno Python
print("\n5. Entorno Python:")
print(f"   Python: {sys.version}")
print(f"   Ejecutable: {sys.executable}")
print(f"   Directorio: {os.getcwd()}")