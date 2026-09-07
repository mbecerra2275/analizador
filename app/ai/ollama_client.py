# app/ai/ollama_client.py
import requests
import json
import socket
import time
import logging

# Configurar logging para ver progreso
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, model="qwen2.5-coder:1.5b", temperature=0.3):
        self.model = model
        self.temperature = temperature
        self.url = "http://127.0.0.1:11434/api/generate"
        self.available = False
        self._warmed_up = False
        self._check_ollama()
        # Intentar warm-up en segundo plano
        if self.available:
            self._warm_up_model()

    def _warm_up_model(self):
        """Pre-carga el modelo en memoria"""
        if self._warmed_up:
            return
        
        print("🔥 Calentando modelo Qwen (puede tomar 20-40s)...")
        try:
            response = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "prompt": "Hola",  # Prompt simple para cargar
                    "stream": False,
                    "options": {"num_predict": 10}  # Respuesta corta
                },
                timeout=120  # Timeout más largo para warm-up
            )
            
            if response.status_code == 200:
                self._warmed_up = True
                print("✅ Modelo cargado y listo")
            else:
                print(f"⚠️ Warm-up con status {response.status_code}")
                # Asumimos que se cargó parcialmente
                self._warmed_up = True
                
        except requests.exceptions.Timeout:
            print("⏱️ Warm-up timeout - puede ser normal en primera ejecución")
            # El modelo puede haber quedado cargado aunque el timeout ocurra
            self._warmed_up = True
        except Exception as e:
            print(f"⚠️ Error en warm-up: {str(e)[:50]}")
            self._warmed_up = True  # Intentaremos de todas formas

    def _check_ollama(self):
        """Verifica conexión con Ollama con timeout más largo"""
        try:
            # 1. Verificar puerto
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # Aumentado de 2 a 5 segundos
            result = sock.connect_ex(('127.0.0.1', 11434))
            sock.close()
            
            if result != 0:
                print(f"🔍 Ollama: ❌ Puerto 11434 no accesible")
                return False
            
            # 2. Health check con timeout más largo
            print("🔍 Verificando Ollama API...")
            r = requests.post(
                self.url,
                json={"model": self.model, "prompt": "test", "stream": False},
                timeout=10  # Aumentado de 5 a 10 segundos
            )
            self.available = r.status_code == 200
            print(f"🔍 Ollama: {'✅ Disponible' if self.available else '❌ No disponible'}")
            return self.available
            
        except requests.exceptions.Timeout:
            print("🔍 Ollama: ⏱️ Timeout en health check - puede estar cargando")
            self.available = True  # Asumimos que está disponible
            return True
        except Exception as e:
            print(f"🔍 Ollama: ❌ Error - {str(e)[:80]}")
            self.available = False
            return False

    def analyze(self, prompt, max_retries=3):
        """Analiza con retries automáticos"""
        if not self.available:
            print("🔄 Intentando reconectar con Ollama...")
            self._check_ollama()
            if not self.available:
                return "⚠️ Ollama no disponible"
        
        # Warm-up si no está caliente
        if not self._warmed_up:
            print("🔄 Calentando modelo...")
            self._warm_up_model()
        
        for attempt in range(max_retries):
            try:
                print(f"🧠 Enviando prompt a IA (intento {attempt+1}/{max_retries})...")
                
                response = requests.post(
                    self.url,
                    json={
                        "model": self.model,
                        "prompt": prompt[:1500],
                        "stream": False,
                        "temperature": self.temperature,
                        "options": {"num_predict": 600}
                    },
                    timeout=120  # Aumentado de 90 a 120 segundos
                )
                
                if response.status_code == 200:
                    result = response.json().get("response", "Sin respuesta")
                    print(f"✅ Análisis IA completado")
                    return result
                else:
                    print(f"⚠️ Status inesperado: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                wait_time = min(5 * (attempt + 1), 20)
                print(f"⏱️ Timeout (intento {attempt+1}) - esperando {wait_time}s")
                time.sleep(wait_time)
                
            except requests.exceptions.ConnectionError:
                print(f"🔌 Error de conexión (intento {attempt+1})")
                self.available = False
                self._check_ollama()
                time.sleep(3)
                
            except Exception as e:
                print(f"❌ Error: {str(e)[:80]}")
                time.sleep(2)
        
        return f"Error después de {max_retries} intentos"

    def analyze_errors(self, errors, context=""):
        """Análisis de errores con agrupación inteligente"""
        if not errors:
            return "No hay errores para analizar"
        
        print(f"📊 Agrupando {len(errors)} errores...")
        grouped = self._group_similar_errors(errors)
        print(f"📊 {len(grouped)} grupos de errores identificados")
        
        # Construir prompt
        prompt = f"Contexto: {context}\n\n"
        prompt += f"Total de errores únicos: {len(grouped)}\n\n"
        prompt += "Errores encontrados:\n"
        
        for i, error in enumerate(grouped[:5], 1):
            entry = error['entry']
            count = error.get('count', 1)
            prompt += f"{i}. [{count} ocurrencias] {entry.message[:200]}\n"
        
        prompt += "\nAnaliza: 1) Causa raíz principal 2) 3 recomendaciones. Respuesta corta y específica."
        
        return self.analyze(prompt)
    
    def _group_similar_errors(self, errors):
        """Agrupa errores similares basados en el mensaje"""
        grouped = {}
        
        for error in errors:
            entry = error['entry']
            # Usar primeros 100 caracteres como clave de agrupación
            key = entry.message[:100].strip().lower()
            
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