# app/ai/multi_ai_analyzer.py
import json
from typing import List, Dict
from .ollama_client import OllamaClient

class MultiAIAnalyzer:
    """Analiza bloques con diferentes modelos IA"""
    
    def __init__(self):
        self.models = {
            'qwen': OllamaClient('qwen2.5-coder:1.5b'),
            'tiny': OllamaClient('tinyllama:latest'),
            'llama': OllamaClient('llama2:latest'),
        }
        self.results = []
    
    def analyze_block(self, block: Dict, model_name: str = 'qwen') -> Dict:
        """Analiza un bloque con un modelo específico"""
        
        client = self.models.get(model_name)
        if not client:
            return {'error': f'Modelo {model_name} no encontrado'}
        
        if not client.available:
            return {'error': f'Modelo {model_name} no disponible'}
        
        # Construir prompt para el bloque
        prompt = self._build_block_prompt(block)
        
        # Obtener análisis
        analysis = client.analyze(prompt)
        
        return {
            'block_id': block['block_id'],
            'model': model_name,
            'analysis': analysis,
            'correlation_ids': block['correlation_ids'],
            'line_range': f"{block['start_line']}-{block['end_line']}",
            'status': 'success' if analysis else 'error'
        }
    
    def analyze_all_blocks(self, blocks: List[Dict], models: List[str] = None) -> List[Dict]:
        """Analiza todos los bloques con múltiples modelos"""
        
        if not models:
            models = list(self.models.keys())
        
        results = []
        
        for block in blocks:
            block_results = []
            for model_name in models:
                print(f"🧠 Analizando bloque {block['block_id']} con {model_name}...")
                result = self.analyze_block(block, model_name)
                block_results.append(result)
            
            results.append({
                'block_id': block['block_id'],
                'analyses': block_results,
                'consensus': self._get_consensus(block_results)
            })
        
        self.results = results
        return results
    
    def _build_block_prompt(self, block: Dict) -> str:
        """Construye prompt para un bloque"""
        return f"""
Analiza este bloque de log de Kubernetes (líneas {block['start_line']}-{block['end_line']}):

{block['content'][:2000]}

Correlation IDs encontrados: {len(block['correlation_ids'])}

Dame:
1. Errores críticos encontrados (máximo 3)
2. Patrones recurrentes
3. Recomendaciones específicas

Respuesta concisa y técnica.
"""
    
    def _get_consensus(self, analyses: List[Dict]) -> Dict:
        """Obtiene consenso entre múltiples análisis"""
        errors_found = []
        for analysis in analyses:
            if analysis.get('analysis') and 'error' not in analysis['analysis'].lower():
                errors_found.append(analysis['analysis'][:200])
        
        return {
            'total_analyses': len(analyses),
            'successful': len([a for a in analyses if a.get('status') == 'success']),
            'common_patterns': self._extract_common_patterns(errors_found)
        }
    
    def _extract_common_patterns(self, texts: List[str]) -> List[str]:
        """Extrae patrones comunes de múltiples análisis"""
        patterns = []
        keywords = ['Keycloak', 'token', 'autenticación', 'timeout', 'captcha', 'PIN']
        
        for text in texts:
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    patterns.append(keyword)
        
        return list(set(patterns))[:5]
    
    def generate_consolidated_report(self) -> str:
        """Genera reporte consolidado de todos los análisis"""
        report = []
        report.append("# 📊 Análisis Multi-IA Consolidado")
        report.append("")
        report.append(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append(f"**Total bloques analizados:** {len(self.results)}")
        report.append("")
        
        for block_result in self.results:
            report.append(f"## Bloque {block_result['block_id']}")
            report.append("")
            
            for analysis in block_result['analyses']:
                model = analysis.get('model', 'unknown')
                status = analysis.get('status', 'error')
                emoji = '✅' if status == 'success' else '❌'
                
                report.append(f"### {emoji} Modelo: {model}")
                report.append("")
                report.append(analysis.get('analysis', 'Sin análisis'))
                report.append("")
            
            consensus = block_result.get('consensus', {})
            report.append("### 🔍 Consenso")
            report.append(f"- Análisis exitosos: {consensus.get('successful', 0)}/{consensus.get('total_analyses', 0)}")
            report.append(f"- Patrones comunes: {', '.join(consensus.get('common_patterns', ['Ninguno']))}")
            report.append("")
            report.append("---")
            report.append("")
        
        return '\n'.join(report)