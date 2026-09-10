"""
Generador de reportes en formato Markdown y HTML.
"""
import os                                          # Manejo de rutas y apertura de archivos
import re                                          # Expresiones regulares para clasificar errores
import html                                        # Escapar HTML en el reporte HTML
from datetime import datetime                      # Timestamps del reporte
from pathlib import Path                           # Rutas portables
from typing import Dict, Any, List, Tuple          # Tipado


class MarkdownReporter:
    """Genera reportes en formato Markdown (y adicionalmente HTML)."""

    # Patrones de "ruido": HTML de páginas de error (Cloudflare, etc.) que no son
    # errores reales de la aplicación y no deberían contarse como tal.
    NOISE_PATTERNS = [
        r"</?div", r"</?span", r"</?link", r"</?meta", r"</?html",
        r"</?head", r"</?body", r"</?script", r"</?style",
        r"<!--\[if", r"<!\[endif\]", r"<!--.*-->",
        r"cf-error", r"cf-wrapper", r"cf_styles", r"cloudflare",
        r"Please enable cookies", r"cf-no-screenshot",
    ]

    # Palabras clave para clasificar cada error en una categoría legible.
    ERROR_CATEGORIES = [
        ("timeout",     ["timed out", "timeout", "read timed out"]),
        ("conexion",    ["connection refused", "connectexception", "connection reset",
                         "no route to host", "unknownhost"]),
        ("http_503",    ["response code: 503", "statuscode=503", "503"]),
        ("http_521",    ["statuscode=521", "error code: 521", "521"]),
        ("permisos",    ["permission denied", "access denied", "forbidden", "401", "403"]),
        ("no_encontrado", ["not found", "404", "no such file"]),
        ("base_datos",  ["sql", "database", "deadlock", "constraint", "jdbc"]),
    ]

    def __init__(self, output_dir: str = "output/reports"):
        # Directorio donde se guardarán los reportes (.md y .html).
        self.output_dir = Path(output_dir)
        # Aseguramos que exista.
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    def generate(self, data: Dict[str, Any]) -> str:
        """
        Genera un reporte Markdown (y su versión HTML al lado).

        Args:
            data: Datos del análisis.

        Returns:
            Ruta del archivo .md generado (compatibilidad con el código actual).
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_path = self.output_dir / f"analysis_report_{timestamp}.md"
        html_path = self.output_dir / f"analysis_report_{timestamp}.html"

        # Pre-procesamos los datos una sola vez (clasificación, ruido, etc.)
        prepared = self._prepare_data(data)

        # Escribimos ambos formatos.
        md_path.write_text(self._build_markdown(prepared), encoding="utf-8")
        html_path.write_text(self._build_html(prepared), encoding="utf-8")

        return str(md_path)

    # ------------------------------------------------------------------ #
    # Pre-procesamiento común (clasificación de errores y ruido)
    # ------------------------------------------------------------------ #
    def _prepare_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepara los datos: clasifica errores por tipo, separa ruido y
        deduplica mensajes repetidos.

        Devuelve un dict con la misma información pero enriquecida.
        """
        errors_in = data.get("errors", []) or []
        real_errors: List[Dict[str, Any]] = []   # Errores reales de la app
        noise_errors: List[Dict[str, Any]] = []  # Ruido (HTML de páginas de error)
        by_category: Dict[str, int] = {}         # Contador por categoría

        for err in errors_in:
            # Unificamos todos los mensajes del grupo para analizarlos.
            messages = err.get("messages", []) or []
            unique_msgs = self._dedupe(messages)

            # ¿Es ruido? Lo decidimos si la mayoría de los mensajes lo son.
            noise_count = sum(1 for m in unique_msgs if self._is_noise(m))
            is_noise = noise_count > 0 and noise_count >= len(unique_msgs) / 2

            # Clasificamos por categoría según palabras clave.
            category = self._classify(unique_msgs)

            enriched = {
                **err,
                "messages": unique_msgs,
                "unique_count": len(unique_msgs),
                "category": category,
                "is_noise": is_noise,
            }

            if is_noise:
                noise_errors.append(enriched)
            else:
                real_errors.append(enriched)
                by_category[category] = by_category.get(category, 0) + err.get("error_count", 0)

        # Añadimos los datos enriquecidos al dict sin romper el original.
        prepared = dict(data)
        prepared["errors"] = real_errors
        prepared["noise_errors"] = noise_errors
        prepared["by_category"] = by_category

        # Recalculamos el total real de errores (sin ruido).
        summary = dict(prepared.get("summary", {}))
        summary["total_errors_real"] = sum(e.get("error_count", 0) for e in real_errors)
        summary["total_noise"] = sum(e.get("error_count", 0) for e in noise_errors)
        prepared["summary"] = summary

        return prepared

    @staticmethod
    def _dedupe(messages: List[str]) -> List[str]:
        """Elimina mensajes duplicados conservando el orden."""
        seen, out = set(), []
        for m in messages:
            if m not in seen:
                seen.add(m)
                out.append(m)
        return out

    @classmethod
    def _is_noise(cls, msg: str) -> bool:
        """Devuelve True si el mensaje parece HTML/ruido de página de error."""
        low = msg.lower()
        return any(re.search(pat, low) for pat in cls.NOISE_PATTERNS)

    @classmethod
    def _classify(cls, messages: List[str]) -> str:
        """Clasifica un conjunto de mensajes en una categoría conocida."""
        joined = " ".join(messages).lower()
        for category, keywords in cls.ERROR_CATEGORIES:
            if any(k in joined for k in keywords):
                return category
        return "otros"

    # ------------------------------------------------------------------ #
    # Utilidades de presentación
    # ------------------------------------------------------------------ #
    @staticmethod
    def _extract_range(messages: List[str]) -> str:
        """
        Extrae el rango temporal (primero y último timestamp) de los mensajes.
        Si no se encuentra ninguno, devuelve '—'.
        """
        ts_re = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
        found = [ts_re.search(m).group(1) for m in messages if ts_re.search(m)]
        if not found:
            return "—"
        return f"{found[0]} → {found[-1]}"

    @staticmethod
    def _emoji_for(category: str) -> str:
        """Devuelve un emoji representativo según la categoría del error."""
        return {
            "timeout": "⏱️",
            "conexion": "🔌",
            "http_503": "🚫",
            "http_521": "🚫",
            "permisos": "🔒",
            "no_encontrado": "🔍",
            "base_datos": "💾",
            "otros": "⚠️",
        }.get(category, "⚠️")

    # ------------------------------------------------------------------ #
    # Generación de Markdown
    # ------------------------------------------------------------------ #
    def _build_markdown(self, data: Dict[str, Any]) -> str:
        """Construye el contenido del reporte en Markdown (rediseñado)."""
        lines: List[str] = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        summary = data.get("summary", {})
        errors = data.get("errors", [])
        noise = data.get("noise_errors", [])
        by_category = data.get("by_category", {})
        ai = data.get("ai_analysis", {})
        recommendations = data.get("recommendations", []) or []

        # ----- Cabecera -----
        lines += [
            "# 📊 Reporte de Análisis de Logs",
            "",
            f"> **Archivo:** `{data.get('file', 'N/A')}`  ",
            f"> **Fecha:** {now}",
            "",
        ]

        # ----- Resumen ejecutivo -----
        total_errors = summary.get("total_errors_real", summary.get("total_errors", 0))
        status = "🔴 Crítico" if total_errors > 0 else "🟢 OK"
        lines += [
            "## 🎯 Resumen ejecutivo",
            "",
            "| Métrica | Valor | Estado |",
            "|---|---:|---|",
            f"| Total de logs | {summary.get('total_logs', 0):,} | — |",
            f"| Transacciones | {summary.get('total_groups', 0):,} | — |",
            f"| Grupos filtrados | {summary.get('filtered_groups', 0):,} | — |",
            f"| **Errores reales** | **{total_errors:,}** | {status} |",
            f"| Ruido filtrado (HTML/CF) | {summary.get('total_noise', 0):,} | ⚪ Ignorado |",
            "",
        ]

        # ----- Top categorías -----
        if by_category:
            lines += [
                "### 🔝 Errores por tipo",
                "",
                "| Tipo | Ocurrencias |",
                "|---|---:|",
            ]
            for cat, count in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"| {self._emoji_for(cat)} {cat} | {count:,} |")
            lines += ["", "---", ""]

        # ----- Índice -----
        lines += [
            "## 📑 Índice",
            "",
            "1. [Niveles de log](#-niveles-de-log)",
            "2. [Análisis con IA](#-análisis-con-ia)",
            "3. [Detalle de errores](#-detalle-de-errores)",
            "4. [Recomendaciones](#-recomendaciones)",
            "",
            "---",
            "",
        ]

        # ----- Niveles -----
        levels = summary.get("levels", {})
        if levels:
            lines += ["## 📊 Niveles de log", ""]
            for level, count in sorted(levels.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"- **{level}:** {count:,}")
            lines.append("")

        # ----- IA -----
        lines += ["## 🤖 Análisis con IA", "", f"**Estado:** {ai.get('status', 'No disponible')}", ""]
        if ai.get("status") == "success" and ai.get("analysis"):
            lines += [ai["analysis"], ""]
        else:
            lines += ["⚠️ Análisis IA no disponible. Revisar que Ollama esté corriendo.", ""]

        # ----- Detalle de errores -----
        lines += ["## ⚠️ Detalle de errores", ""]
        if not errors:
            lines += ["✅ No se encontraron errores reales.", ""]
        else:
            for i, err in enumerate(errors[:30], 1):  # Mostramos hasta 30 en detalle
                emoji = self._emoji_for(err.get("category", "otros"))
                count = err.get("error_count", 0)
                cat = err.get("category", "otros")
                rng = self._extract_range(err.get("messages", []))

                lines += [
                    f"<details>",
                    f"<summary><b>#{i} — {emoji} {cat} · {count} ocurrencias</b></summary>",
                    "",
                    f"- **Rango temporal:** {rng}",
                    f"- **Mensajes únicos:** {err.get('unique_count', 0)}",
                    "",
                    "**Ejemplos:**",
                    "",
                ]
                for msg in err.get("messages", [])[:5]:
                    lines += ["```", msg, "```", ""]
                if err.get("unique_count", 0) > 5:
                    lines.append(f"_... y {err['unique_count'] - 5} mensajes únicos más_")
                    lines.append("")
                lines += ["</details>", ""]

            if len(errors) > 30:
                lines += [f"_... y {len(errors) - 30} grupos de error más (ver HTML para el listado completo)._", ""]

        # ----- Ruido -----
        if noise:
            lines += [
                "## 🧹 Ruido filtrado (no son errores reales)",
                "",
                f"Se detectaron **{len(noise)}** grupos de líneas que parecen ser HTML de "
                "páginas de error (Cloudflare, etc.). No se cuentan como errores de la aplicación.",
                "",
                "<details>",
                "<summary>Ver ejemplos de ruido</summary>",
                "",
            ]
            for err in noise[:3]:
                for msg in err.get("messages", [])[:2]:
                    lines += ["```", msg, "```", ""]
            lines += ["</details>", ""]

        # ----- Recomendaciones -----
        if recommendations:
            lines += ["## 💡 Recomendaciones", ""]
            for rec in recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        # ----- Pie -----
        lines += [
            "---",
            "",
            "_Reporte generado automáticamente por el Analizador de Logs con IA_",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Generación de HTML (dashboard autocontenido, sin dependencias)
    # ------------------------------------------------------------------ #
    def _build_html(self, data: Dict[str, Any]) -> str:
        """Construye un dashboard HTML autocontenido (CSS + JS embebidos)."""
        summary = data.get("summary", {})
        errors = data.get("errors", [])
        noise = data.get("noise_errors", [])
        by_category = data.get("by_category", {})
        ai = data.get("ai_analysis", {})
        recommendations = data.get("recommendations", []) or []

        total_errors = summary.get("total_errors_real", summary.get("total_errors", 0))
        file_name = html.escape(str(data.get("file", "N/A")))
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Bloque de tarjetas de métricas
        cards = f"""
        <div class="cards">
          <div class="card"><div class="k">Logs</div><div class="v">{summary.get('total_logs', 0):,}</div></div>
          <div class="card"><div class="k">Transacciones</div><div class="v">{summary.get('total_groups', 0):,}</div></div>
          <div class="card danger"><div class="k">Errores reales</div><div class="v">{total_errors:,}</div></div>
          <div class="card muted"><div class="k">Ruido filtrado</div><div class="v">{summary.get('total_noise', 0):,}</div></div>
        </div>
        """

        # Barras por categoría (CSS puro, sin librerías)
        max_cat = max(by_category.values()) if by_category else 1
        bars_html = ""
        for cat, count in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
            pct = int(count / max_cat * 100)
            bars_html += f"""
            <div class="bar-row">
              <div class="bar-label">{self._emoji_for(cat)} {html.escape(cat)}</div>
              <div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>
              <div class="bar-count">{count:,}</div>
            </div>"""

        # Listado de errores colapsables
        items_html = ""
        for i, err in enumerate(errors, 1):
            msgs = "".join(
                f"<pre>{html.escape(m)}</pre>" for m in err.get("messages", [])[:5]
            )
            cat = html.escape(err.get("category", "otros"))
            items_html += f"""
            <details class="err-item">
              <summary>
                <span class="cat {cat}">{self._emoji_for(cat)} {cat}</span>
                <b>#{i}</b> — {err.get('error_count', 0)} ocurrencias
                <span class="range">{html.escape(self._extract_range(err.get('messages', [])))}</span>
              </summary>
              <div class="msgs">{msgs}</div>
            </details>"""

        # Ruido (solo conteo)
        noise_html = ""
        if noise:
            noise_html = f"""
            <h2>🧹 Ruido filtrado</h2>
            <p>{len(noise)} grupos de líneas tipo HTML/Cloudflare. No cuentan como errores de la app.</p>
            """

        # Recomendaciones
        rec_html = ""
        if recommendations:
            rec_html = "<h2>💡 Recomendaciones</h2><ul>" + \
                "".join(f"<li>{html.escape(str(r))}</li>" for r in recommendations) + "</ul>"

        # IA
        ai_status = html.escape(str(ai.get("status", "No disponible")))
        ai_text = html.escape(str(ai.get("analysis", ""))) if ai.get("status") == "success" else ""

        # Plantilla completa
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Reporte de Análisis de Logs</title>
<style>
  :root {{
    --bg:#0f172a; --fg:#e2e8f0; --muted:#94a3b8; --card:#1e293b;
    --accent:#38bdf8; --danger:#ef4444; --warn:#f59e0b; --ok:#22c55e;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
         background: var(--bg); color: var(--fg); padding: 32px; }}
  h1 {{ margin: 0 0 4px; }}
  h2 {{ margin-top: 32px; border-bottom: 1px solid #334155; padding-bottom: 6px; }}
  .meta {{ color: var(--muted); font-size: 14px; margin-bottom: 24px; }}
  .cards {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(180px,1fr));
            gap: 16px; margin: 24px 0; }}
  .card {{ background: var(--card); padding: 16px; border-radius: 10px; }}
  .card .k {{ color: var(--muted); font-size: 13px; }}
  .card .v {{ font-size: 28px; font-weight: 700; margin-top: 6px; }}
  .card.danger .v {{ color: var(--danger); }}
  .card.muted .v {{ color: var(--muted); }}
  .bar-row {{ display:grid; grid-template-columns: 200px 1fr 80px; gap: 10px;
              align-items:center; margin: 8px 0; }}
  .bar-track {{ background:#1e293b; height:14px; border-radius:7px; overflow:hidden; }}
  .bar-fill {{ background: var(--accent); height:100%; }}
  .bar-count {{ text-align:right; color: var(--muted); font-variant-numeric: tabular-nums; }}
  .err-item {{ background: var(--card); border-radius: 8px; margin: 8px 0; padding: 12px 16px; }}
  .err-item summary {{ cursor: pointer; display:flex; gap:12px; align-items:center; flex-wrap:wrap; }}
  .err-item .cat {{ padding: 2px 8px; border-radius: 6px; background:#334155; font-size:12px; }}
  .err-item .cat.timeout {{ background:#7c2d12; }}
  .err-item .cat.conexion {{ background:#7c2d12; }}
  .err-item .cat.http_503, .err-item .cat.http_521 {{ background:#78350f; }}
  .err-item .cat.permisos {{ background:#581c87; }}
  .err-item .range {{ color: var(--muted); font-size: 12px; margin-left: auto; }}
  pre {{ background:#020617; padding:10px; border-radius:6px; overflow-x:auto;
         font-size: 12px; color:#cbd5e1; }}
  input.search {{ width:100%; padding:10px; border-radius:8px; border:1px solid #334155;
                  background:#020617; color: var(--fg); margin: 16px 0; }}
  footer {{ margin-top: 40px; color: var(--muted); font-size: 12px; text-align:center; }}
</style>
</head>
<body>
  <h1>📊 Reporte de Análisis de Logs</h1>
  <div class="meta">📄 {file_name} · 🕒 {now}</div>

  {cards}

  <h2>🔝 Errores por tipo</h2>
  {bars_html or '<p>Sin errores clasificados.</p>'}

  <h2>🤖 Análisis con IA</h2>
  <p><b>Estado:</b> {ai_status}</p>
  <p>{ai_text}</p>

  {noise_html}

  <h2>⚠️ Detalle de errores</h2>
  <input class="search" id="q" placeholder="Buscar en los errores...">
  <div id="errs">{items_html or '<p>Sin errores reales.</p>'}</div>

  {rec_html}

  <footer>Reporte generado automáticamente por el Analizador de Logs con IA</footer>

<script>
  // Filtro simple: muestra/oculta items según el texto buscado.
  const q = document.getElementById('q');
  q.addEventListener('input', () => {{
    const term = q.value.toLowerCase();
    document.querySelectorAll('#errs details').forEach(d => {{
      d.style.display = d.textContent.toLowerCase().includes(term) ? '' : 'none';
    }});
  }});
</script>
</body>
</html>"""