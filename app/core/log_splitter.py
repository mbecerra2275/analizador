"""
Divisor de archivos de log en bloques.

Los archivos de log muy grandes (cientos de MB) no caben cómodos en memoria
ni en el contexto del modelo IA. Este módulo los trocea en bloques de N líneas
para poder procesarlos por partes (análisis paralelo o secuencial por lotes).

Cada bloque conserva su rango de líneas originales y la lista de
correlation-ids que contiene, de modo que bloques del mismo flujo
puedan reagruparse después del análisis.
"""
import os
from typing import List, Dict
from datetime import datetime


class LogSplitter:
    """Divide un archivo de log en bloques de tamaño fijo (por nº de líneas)."""

    def __init__(self, lines_per_block: int = 5000):
        # Nº de líneas por bloque. 5000 es un equilibrio entre usar poca
        # memoria y no romper demasiadas transacciones entre bloques.
        self.lines_per_block = lines_per_block

    def split_file(self, filepath: str) -> List[Dict]:
        """
        Trocea un archivo de log en bloques consecutivos.

        Args:
            filepath: Ruta del archivo .log a dividir.

        Returns:
            Lista de dicts, uno por bloque, con las claves:
            - block_id: nº de bloque (1-indexed, para mostrar al usuario).
            - start_line / end_line: rango de líneas originales (1-indexed).
            - total_lines: nº real de líneas del bloque (el último suele ser menor).
            - correlation_ids: ids de correlación únicos hallados en el bloque.
            - content: texto completo del bloque (para enviar al analizador).
            - file_size: tamaño en caracteres (aprox. bytes en ASCII).
        """
        blocks = []

        # Se lee el archivo completo; para logs gigantes (>1GB) convendría
        # lectura por streaming, pero readlines es suficiente en la práctica.
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total_lines = len(lines)
        # División entera + 1 para cubrir el resto final (aunque sea exacto,
        # el último bloque vacío se evita con el min() de abajo... salvo que
        # total_lines sea múltiplo exacto, caso en que sobra un bloque vacío).
        num_blocks = (total_lines // self.lines_per_block) + 1

        for i in range(num_blocks):
            # Índices 0-based para el slice; las líneas reportadas son 1-based.
            start = i * self.lines_per_block
            end = min(start + self.lines_per_block, total_lines)

            block_lines = lines[start:end]

            # Extraer correlation-ids del bloque (sirve para saber qué flujos
            # tocan este bloque y reagruparlos tras el análisis por lotes).
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
        """
        Extrae los correlation-ids únicos presentes en unas líneas.

        Args:
            lines: Líneas de log (un bloque).

        Returns:
            Lista de ids únicos (formato ssff-correlation-id=<hex>).
        """
        import re
        # set para deduplicar: un mismo flujo aparece en muchas líneas.
        ids = set()
        # Patrón específico del formato SSFF (ids hexadecimales).
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