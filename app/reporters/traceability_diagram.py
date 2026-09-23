"""
Generador de diagramas de trazabilidad para logs.
Genera diagramas Mermaid y Graphviz DOT basados en la correlación de logs.
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TraceabilityDiagramGenerator:
    """Genera diagramas de trazabilidad a partir de resultados de análisis."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else Path("output/reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_from_analysis(self, analysis_result: Dict[str, Any], base_filename: str) -> Dict[str, str]:
        """
        Genera diagramas de trazabilidad a partir del resultado del análisis.

        Args:
            analysis_result: Diccionario con el resultado del análisis (de AnalysisService)
            base_filename: Nombre base para los archivos (sin extensión)

        Returns:
            Diccionario con rutas de archivos generados
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"{base_filename}_{timestamp}"

        generated = {}

        # 1. Diagrama de flujo de correlación (Mermaid)
        mermaid_path = self.output_dir / f"{base}_traceability.mmd"
        mermaid_content = self._generate_mermaid_correlation_flow(analysis_result)
        mermaid_path.write_text(mermaid_content, encoding='utf-8')
        generated['mermaid'] = str(mermaid_path)
        logger.info(f"Diagrama Mermaid generado: {mermaid_path}")

        # 2. Diagrama de propagación de errores (Mermaid)
        error_mermaid_path = self.output_dir / f"{base}_error_propagation.mmd"
        error_mermaid_content = self._generate_mermaid_error_propagation(analysis_result)
        error_mermaid_path.write_text(error_mermaid_content, encoding='utf-8')
        generated['error_mermaid'] = str(error_mermaid_path)

        # 3. Timeline de eventos (Mermaid)
        timeline_path = self.output_dir / f"{base}_timeline.mmd"
        timeline_content = self._generate_mermaid_timeline(analysis_result)
        timeline_path.write_text(timeline_content, encoding='utf-8')
        generated['timeline'] = str(timeline_path)

        # 4. Intentar generar Graphviz DOT si está disponible
        dot_path = self.output_dir / f"{base}_traceability.dot"
        dot_content = self._generate_dot_correlation_flow(analysis_result)
        dot_path.write_text(dot_content, encoding='utf-8')
        generated['dot'] = str(dot_path)

        # 5. Intentar renderizar a PNG (mermaid-cli > Graphviz)
        mmd_files = [mermaid_path, error_mermaid_path, timeline_path]
        rendered = self._try_render_png(mmd_files, dot_path)
        if rendered:
            generated['rendered_png'] = rendered
            generated['rendered_type'] = 'mermaid-cli' if 'mermaid' in rendered else 'graphviz'

        return generated

    def _generate_mermaid_correlation_flow(self, result: Dict[str, Any]) -> str:
        """Genera diagrama de flujo de correlación en formato Mermaid."""
        lines = []
        lines.append("```mermaid")
        lines.append("flowchart TD")
        lines.append("    %% Diagrama de Trazabilidad - Flujo de Correlación")
        lines.append("    %% Generado automáticamente por Log Analyzer")
        lines.append("")

        groups = result.get('errors', [])
        if not groups:
            lines.append("    NoData[No hay datos de correlación disponibles]")
            lines.append("```")
            return "\n".join(lines)

        # Nodo inicial
        lines.append("    Start([Inicio del Análisis])")

        # Agrupar por correlation ID
        for i, group in enumerate(groups):
            corr_id = group.get('correlation_id', f'group_{i}')
            short_id = corr_id[:12] + "..." if len(corr_id) > 15 else corr_id
            error_count = group.get('error_count', 0)
            merged = group.get('merged_from', 1)

            # Determinar color/estilo según severidad
            if error_count > 5:
                node_style = ":::critical"
            elif error_count > 1:
                node_style = ":::warning"
            else:
                node_style = ":::info"

            # Etiqueta del nodo
            label = f"{short_id}\\n{error_count} errores"
            if merged > 1:
                label += f"\\n(fusionado {merged} IDs)"

            node_id = f"G{i}"
            lines.append(f'    {node_id}["{label}"]{node_style}')

            # Conectar desde inicio
            if i == 0:
                lines.append(f"    Start --> {node_id}")
            else:
                prev_id = f"G{i-1}"
                lines.append(f"    {prev_id} --> {node_id}")

            # Agregar mensajes de error como sub-nodos
            messages = group.get('messages', [])
            for j, msg in enumerate(messages[:3]):  # Máximo 3 mensajes por grupo
                msg_short = msg[:50].replace('"', "'").replace("\n", " ")
                msg_node = f"{node_id}_M{j}"
                lines.append(f'    {msg_node}["{msg_short}"]:::message')
                lines.append(f"    {node_id} -.-> {msg_node}")

        # Estilos
        lines.append("")
        lines.append("    classDef critical fill:#ff6b6b,color:#fff,stroke:#c92a2a,stroke-width:2px;")
        lines.append("    classDef warning fill:#ffd43b,color:#333,stroke:#f08c00,stroke-width:2px;")
        lines.append("    classDef info fill:#74c0fc,color:#333,stroke:#1864ab,stroke-width:2px;")
        lines.append("    classDef message fill:#e9ecef,color:#333,stroke:#adb5bd,stroke-dasharray: 5 5;")

        lines.append("```")
        return "\n".join(lines)

    def _generate_mermaid_error_propagation(self, result: Dict[str, Any]) -> str:
        """Genera diagrama de propagación de errores en formato Mermaid."""
        lines = []
        lines.append("```mermaid")
        lines.append("graph LR")
        lines.append("    %% Diagrama de Propagación de Errores")
        lines.append("")

        errors = result.get('errors', [])
        if not errors:
            lines.append("    NoErrors[No se detectaron errores]")
            lines.append("```")
            return "\n".join(lines)

        # Categorizar errores por tipo
        categories = {}
        for error in errors:
            messages = error.get('messages', [])
            for msg in messages:
                cat = self._categorize_error(msg)
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(error)

        # Nodo central
        lines.append("    Root[Sistema Analizado]")

        # Nodos por categoría
        cat_nodes = []
        for cat, cat_errors in categories.items():
            cat_id = cat.lower().replace(" ", "_")
            count = len(cat_errors)
            lines.append(f'    {cat_id}["{cat}\\n{count} ocurrencias"]')
            lines.append(f"    Root --> {cat_id}")
            cat_nodes.append(cat_id)

            # Sub-nodos para correlation IDs
            for i, err in enumerate(cat_errors[:5]):
                corr_id = err.get('correlation_id', 'unknown')
                short_id = corr_id[:10]
                err_node = f"{cat_id}_E{i}"
                lines.append(f'    {err_node}["{short_id}"]')
                lines.append(f"    {cat_id} --> {err_node}")

        # Estilos por categoría
        lines.append("")
        style_colors = {
            'timeout': '#ff6b6b',
            'connection': '#ff8787',
            'database': '#ffd43b',
            'permission': '#ffa94d',
            'not_found': '#74c0fc',
            'memory': '#da77f2',
            'other': '#adb5bd'
        }
        for cat in categories:
            cat_id = cat.lower().replace(" ", "_")
            color = style_colors.get(cat, '#adb5bd')
            lines.append(f"    classDef {cat_id} fill:{color},color:#333;")
            lines.append(f"    class {cat_id} {cat_id};")

        lines.append("```")
        return "\n".join(lines)

    def _generate_mermaid_timeline(self, result: Dict[str, Any]) -> str:
        """Genera timeline de eventos en formato Mermaid."""
        lines = []
        lines.append("```mermaid")
        lines.append("timeline")
        lines.append("    title Timeline de Eventos - Análisis de Logs")
        lines.append("")

        errors = result.get('errors', [])
        if not errors:
            lines.append("    Sin eventos de error registrados")
            lines.append("```")
            return "\n".join(lines)

        # Agrupar por timestamp aproximado
        for error in errors[:10]:  # Top 10
            timestamp = error.get('timestamp', '')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    time_str = timestamp[:19]
            else:
                time_str = "Tiempo desconocido"

            corr_id = error.get('correlation_id', 'unknown')
            short_id = corr_id[:12]
            count = error.get('error_count', 0)
            messages = error.get('messages', [])

            event_desc = f"{short_id}: {count} errores"
            if messages:
                first_msg = messages[0][:60].replace('"', "'")
                event_desc += f" - {first_msg}"

            lines.append(f'    {time_str} : {event_desc}')

        lines.append("```")
        return "\n".join(lines)

    def _generate_dot_correlation_flow(self, result: Dict[str, Any]) -> str:
        """Genera diagrama Graphviz DOT para flujo de correlación."""
        lines = []
        lines.append('digraph Traceability {')
        lines.append('    rankdir=TB;')
        lines.append('    node [fontname="Segoe UI", fontsize=10];')
        lines.append('    edge [fontname="Segoe UI", fontsize=9];')
        lines.append('    label="Diagrama de Trazabilidad - Flujo de Correlación";')
        lines.append('    labelloc="t";')
        lines.append('    fontsize=14;')
        lines.append('')

        # Nodo inicial
        lines.append('    Start [label="Inicio del Análisis", shape=ellipse, style=filled, fillcolor="#e3f2fd", color="#1565c0"];')

        errors = result.get('errors', [])
        if not errors:
            lines.append('    NoData [label="No hay datos de correlación", shape=box, style=filled, fillcolor="#f5f5f5"];')
            lines.append('    Start -> NoData;')
            lines.append('}')
            return "\n".join(lines)

        prev_node = "Start"
        for i, group in enumerate(errors):
            corr_id = group.get('correlation_id', f'group_{i}')
            short_id = corr_id[:12] + "..." if len(corr_id) > 15 else corr_id
            error_count = group.get('error_count', 0)
            merged = group.get('merged_from', 1)

            # Color según severidad
            if error_count > 5:
                fill_color = "#ffcdd2"
                border_color = "#c62828"
            elif error_count > 1:
                fill_color = "#fff9c4"
                border_color = "#f57f17"
            else:
                fill_color = "#bbdefb"
                border_color = "#1565c0"

            label = f'{short_id}\\n{error_count} errores'
            if merged > 1:
                label += f'\\n(fusionado {merged} IDs)'

            node_id = f'G{i}'
            lines.append(f'    {node_id} [label="{label}", shape=box, style="filled,rounded", fillcolor="{fill_color}", color="{border_color}"];')
            lines.append(f'    {prev_node} -> {node_id} [penwidth=2];')

            # Mensajes de error
            messages = group.get('messages', [])
            for j, msg in enumerate(messages[:2]):
                msg_short = msg[:60].replace('"', '\\"').replace("\n", "\\n")
                msg_node = f'{node_id}_M{j}'
                lines.append(f'    {msg_node} [label="{msg_short}", shape=note, style=filled, fillcolor="#f5f5f5", color="#9e9e9e", fontcolor="#616161", fontsize=8];')
                lines.append(f'    {node_id} -> {msg_node} [style=dashed, color="#9e9e9e", penwidth=1];')

            prev_node = node_id

        lines.append('}')
        return "\n".join(lines)

    def _categorize_error(self, message: str) -> str:
        """Categoriza un mensaje de error."""
        msg_lower = message.lower()
        if any(kw in msg_lower for kw in ['timeout', 'timed out']):
            return 'Timeout'
        elif any(kw in msg_lower for kw in ['connection', 'connect', 'refused', 'unreachable']):
            return 'Connection'
        elif any(kw in msg_lower for kw in ['database', 'sql', 'db ', 'jdbc']):
            return 'Database'
        elif any(kw in msg_lower for kw in ['permission', 'access denied', 'forbidden', 'unauthorized']):
            return 'Permission'
        elif any(kw in msg_lower for kw in ['not found', '404', 'no such']):
            return 'Not Found'
        elif any(kw in msg_lower for kw in ['memory', 'oom', 'out of memory']):
            return 'Memory'
        else:
            return 'Other'

    def _try_render_png(self, mmd_files: List[Path], dot_path: Path) -> Optional[str]:
        """
        Intenta renderizar diagramas a PNG.
        Prioridad 1: mermaid-cli (renderiza .mmd directamente)
        Prioridad 2: Graphviz (renderiza .dot)
        """
        import subprocess

        # --- Prioridad 1: mermaid-cli (npx @mermaid-js/mermaid-cli) ---
        for mmd_file in mmd_files:
            png_path = mmd_file.with_suffix('.png')
            try:
                # Verificar si mermaid-cli está disponible
                result = subprocess.run(
                    ['npx', '--version'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    # mermaid-cli disponible, renderizar
                    cmd = [
                        'npx', '-y', '@mermaid-js/mermaid-cli',
                        '-i', str(mmd_file),
                        '-o', str(png_path),
                        '--backgroundColor', 'white',
                        '--width', '1200'
                    ]
                    subprocess.run(cmd, check=True, timeout=60, capture_output=True)
                    logger.info(f"Diagrama PNG generado con mermaid-cli: {png_path}")
                    return str(png_path)
            except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                pass  # mermaid-cli no disponible, intentar Graphviz
            except Exception as e:
                logger.debug(f"Error con mermaid-cli: {e}")

        # --- Prioridad 2: Graphviz (renderiza .dot) ---
        def _find_dot_executable():
            """Encuentra la ruta completa del ejecutable dot."""
            # 1. Intentar en PATH
            try:
                result = subprocess.run(['dot', '-V'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return 'dot'
            except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                pass

            # 2. Rutas comunes en Windows
            if sys.platform == 'win32':
                common_paths = [
                    r"C:\Program Files\Graphviz\bin\dot.exe",
                    r"C:\Program Files (x86)\Graphviz\bin\dot.exe",
                    os.path.expandvars(r"%USERPROFILE%\AppData\Local\Microsoft\WinGet\Packages\Graphviz.Graphviz_*\bin\dot.exe"),
                ]
                for path in common_paths:
                    if '*' in path:
                        import glob
                        matches = glob.glob(path)
                        if matches:
                            return matches[0]
                    elif os.path.exists(path):
                        return path

            # 3. Buscar en Program Files
            if sys.platform == 'win32':
                for root in [r"C:\Program Files", r"C:\Program Files (x86)"]:
                    graphviz_bin = os.path.join(root, "Graphviz", "bin", "dot.exe")
                    if os.path.exists(graphviz_bin):
                        return graphviz_bin

            return None

        dot_exe = _find_dot_executable()
        if dot_exe:
            try:
                png_path = dot_path.with_suffix('.png')
                subprocess.run([dot_exe, '-Tpng', str(dot_path), '-o', str(png_path)],
                               check=True, timeout=30, capture_output=True)
                logger.info(f"Diagrama PNG generado con Graphviz: {png_path}")

                # También SVG
                svg_path = dot_path.with_suffix('.svg')
                subprocess.run([dot_exe, '-Tsvg', str(dot_path), '-o', str(svg_path)],
                               check=True, timeout=30, capture_output=True)
                logger.info(f"Diagrama SVG generado con Graphviz: {svg_path}")

                return str(png_path)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                logger.debug(f"Error renderizando con Graphviz: {e}")
            except Exception as e:
                logger.warning(f"Error inesperado al renderizar Graphviz: {e}")

        return None


def generate_traceability_diagram(analysis_result: Dict[str, Any], output_dir: str, filename: str) -> Dict[str, str]:
    """
    Función de conveniencia para generar diagrama de trazabilidad.

    Args:
        analysis_result: Resultado del análisis de AnalysisService
        output_dir: Directorio de salida
        filename: Nombre base del archivo (ej: nombre del archivo de log)

    Returns:
        Diccionario con rutas de archivos generados
    """
    generator = TraceabilityDiagramGenerator(output_dir)
    return generator.generate_from_analysis(analysis_result, filename)