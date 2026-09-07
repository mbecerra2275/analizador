# app/config.py
import os
from typing import Dict

def load_config(config_file: str = None) -> Dict:
    """Carga configuración desde archivo YAML"""
    
    default_config = {
        'output_dir': 'output/reports/',
        'ai_model': 'qwen2.5-coder:1.5b',
        'temperature': 0.3,
        'max_errors_for_ai': 10,
        'verbose': False,
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
    }
    
    if config_file and os.path.exists(config_file):
        try:
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    default_config.update(user_config)
        except:
            pass
    
    return default_config