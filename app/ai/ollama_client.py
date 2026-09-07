import requests
import json
import socket
import time

class OllamaClient:
    def __init__(self, model="qwen2.5-coder:1.5b", temperature=0.3):
        self.model = model
        self.temperature = temperature
        self.url = "http://127.0.0.1:11434/api/generate"
        self.available = False
        self._check_ollama()

    def _check_ollama(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', 11434))
            sock.close()
            
            if result != 0:
                print(f"🔍 Ollama: ❌ Puerto 11434 no accesible")
                return False
            
            r = requests.post(
                self.url,
                json={"model": self.model, "prompt": "test", "stream": False},
                timeout=5
            )
            self.available = r.status_code == 200
            print(f"🔍 Ollama: {'✅ Disponible' if self.available else '❌ No disponible'}")
            return self.available
        except Exception as e:
            print(f"🔍 Ollama: ❌ Error - {str(e)[:80]}")
            self.available = False
            return False

    def analyze(self, prompt):
        if not self.available:
            self._check_ollama()
            if not self.available:
                return "⚠️ Ollama no disponible"
        
        try:
            r = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "prompt": prompt[:1500],
                    "stream": False,
                    "temperature": self.temperature,
                    "options": {"num_predict": 600}
                },
                timeout=90
            )
            return r.json().get("response", "Sin respuesta")
        except Exception as e:
            return f"Error: {str(e)[:100]}"

    def analyze_errors(self, errors, context=""):
        if not errors:
            return "No hay errores para analizar"
        
        # Agrupar errores similares antes de enviar
        grouped = self._group_similar_errors(errors)
        
        prompt = f"Contexto: {context}\n\n"
        prompt += f"Total de errores únicos: {len(grouped)}\n\n"
        prompt += "Errores encontrados:\n"
        
        for i, error in enumerate(grouped[:5], 1):
            entry = error['entry']
            count = error.get('count', 1)
            prompt += f"{i}. [{count} ocurrencias] {entry.message[:200]}\n"
        
        prompt += "\nAnaliza: 1) Causa raíz principal 2) 3 recomendaciones. Respuesta corta."
        
        return self.analyze(prompt)
    
    def _group_similar_errors(self, errors):
        """Agrupa errores similares basados en el mensaje"""
        grouped = {}
        
        for error in errors:
            entry = error['entry']
            # Usar primeros 100 caracteres como clave de agrupación
            key = entry.message[:100].strip()
            
            if key not in grouped:
                grouped[key] = {
                    'entry': entry,
                    'count': 1,
                    'type': error.get('type', 'UNKNOWN'),
                    'severity': error.get('severity', 'UNKNOWN')
                }
            else:
                grouped[key]['count'] += 1
        
        # Ordenar por frecuencia
        return sorted(grouped.values(), key=lambda x: x['count'], reverse=True)