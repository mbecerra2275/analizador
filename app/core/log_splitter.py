# app/core/log_splitter.py
import os
from typing import List, Dict
from datetime import datetime

class LogSplitter:
    """Divide logs en bloques para análisis paralelo"""
    
    def __init__(self, lines_per_block: int = 5000):
        self.lines_per_block = lines_per_block
    
    def split_file(self, filepath: str) -> List[Dict]:
        """Divide un archivo de log en bloques"""
        blocks = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        num_blocks = (total_lines // self.lines_per_block) + 1
        
        for i in range(num_blocks):
            start = i * self.lines_per_block
            end = min(start + self.lines_per_block, total_lines)
            
            block_lines = lines[start:end]
            
            # Extraer correlation-ids del bloque
            corr_ids = self._extract_correlation_ids(block_lines)
            
            blocks.append({
                'block_id': i + 1,
                'start_line': start + 1,
                'end_line': end,
                'total_lines': len(block_lines),
                'correlation_ids': corr_ids,
                'content': ''.join(block_lines),
                'file_size': len(''.join(block_lines))
            })
        
        return blocks
    
    def _extract_correlation_ids(self, lines: List[str]) -> List[str]:
        """Extrae correlation-ids únicos del bloque"""
        import re
        ids = set()
        pattern = r'ssff-correlation-id=([a-f0-9]+)'
        for line in lines:
            match = re.search(pattern, line)
            if match:
                ids.add(match.group(1))
        return list(ids)
    
    def get_block_summary(self, blocks: List[Dict]) -> str:
        """Resumen de los bloques creados"""
        summary = []
        summary.append(f"📊 Log dividido en {len(blocks)} bloques")
        summary.append("")
        summary.append("| Bloque | Líneas | Correlation IDs | Tamaño |")
        summary.append("|--------|--------|-----------------|--------|")
        for block in blocks:
            summary.append(
                f"| {block['block_id']} | {block['total_lines']} | "
                f"{len(block['correlation_ids'])} | {block['file_size']//1024}KB |"
            )
        return '\n'.join(summary)