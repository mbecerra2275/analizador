"""
Generador de reportes en formato Markdown y HTML.
"""
import os
import re
import html
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple


class MarkdownReporter:
    """Genera reportes en formato Markdown (y adicionalmente HTML)."""

    NOISE_PATTERNS = [
        r"</?div", r"</?span", r"</?link", r"</?meta", r"</?html",
        r"</?head", r"</?body", r"</?script", r"</?style",
        r"<!--\[if", r"<!\[endif\]", r"<!--.*-->",
        r"cf-error", r"cf-wrapper", r"cf_styles", r"cloudflare",
        r"Please enable cookies", r"cf-no-screenshot",
    ]

    ERROR_CATEGORIES = [
        ("timeout",       ["timed out", "timeout", "read timed out"]),
        ("conexion",      ["connection refused", "connectexception", "connection reset",
                           "no route to host", "unknownhost"]),
        ("http_503",      ["response code: 503", "statuscode=503", " 503 "]),
        ("http_521",      ["statuscode=521", "error code: 521", " 521 "]),
        ("permisos",      ["permission denied", "access denied", "forbidden", "401", "403"]),
        ("no_encontrado", ["not found", "404", "no such file"]),
        ("base_datos",    ["sql", "database", "deadlock", "constraint", "jdbc"]),
        ("nullpointer",   ["cannot read property", "cannot read properties",
                           "of undefined", "of null", "nullpointer", "npe"]),
    ]

    def __init__(self, output_dir: str = "output/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    def generate(self, data: Dict[str, Any]) -> str:
        """
        Genera un reporte Markdown (y su versión HTML al lado).

        Args:
            data: Datos del análisis. Debe contener:
                - file: ruta del archivo analizado
                - summary: dict con total_logs, total_groups, etc.
                - errors: lista de grupos de error
                - ai_analysis: dict con status y analysis (nuevo formato)
                - recommendations: lista de strings (opcional)

        Returns:
            Ruta del archivo .md generado.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_path = self.output_dir / f"analysis_report_{timestamp}.md"
        html_path = self.output_dir / f"analysis_report_{timestamp}.html"

        prepared = self._prepare_data(data)

        md_path.write_text(self._build_markdown(prepared), encoding="utf-8")
        html_path.write_text(self._build_html(prepared), encoding="utf-8")

        return str(md_path)

    # ------------------------------------------------------------------ #
    # Pre-procesamiento común
    # ------------------------------------------------------------------ #
    def _prepare_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        errors_in = data.get("errors", []) or []
        real_errors: List[Dict[str, Any]] = []
        noise_errors: List[Dict[str, Any]] = []
        by_category: Dict[str, int] = {}

        for err in errors_in:
            messages = err.get("messages", []) or []
            # Si viene 'message' único (como en tu pipeline), lo tratamos también
            if not messages and err.get("message"):
                messages = [err["message"]]
            if not messages and err.get("raw"):
                messages = [err["raw"]]

            unique_msgs = self._dedupe(messages)

            noise_count = sum(1 for m in unique_msgs if self._is_noise(m))
            is_noise = noise_count > 0 and noise_count >= len(unique_msgs) / 2

            category = err.get("category") or self._classify(unique_msgs)

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
                by_category[category] = by_category.get(category, 0) + err.get("error_count", 1)

        prepared = dict(data)
        prepared["errors"] = real_errors
        prepared["noise_errors"] = noise_errors
        prepared["by_category"] = by_category

        summary = dict(prepared.get("summary", {}))
        summary["total_errors_real"] = sum(e.get("error_count", 1) for e in real_errors)
        summary["total_noise"] = sum(e.get("error_count", 1) for e in noise_errors)
        prepared["summary"] = summary

        return prepared

    @staticmethod
    def _dedupe(messages: List[str]) -> List[str]:
        seen, out = set(), []
        for m in messages:
            if m not in seen:
                seen.add(m)
                out.append(m)
        return out

    @classmethod
    def _is_noise(cls, msg: str) -> bool:
        low = msg.lower()
        return any(re.search(pat, low) for pat in cls.NOISE_PATTERNS)

    @classmethod
    def _classify(cls, messages: List[str]) -> str:
        joined = " ".join(messages).lower()
        for category, keywords in cls.ERROR_CATEGORIES:
            if any(k in joined for k in keywords):
                return category
        return "otros"

    # ------------------------------------------------------------------ #
    # Utilidades
    # ------------------------------------------------------------------ #
    @staticmethod
    def _extract_range(messages: List[str]) -> str:
        ts_re = re.compile(r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})")
        found = [ts_re.search(m).group(1) for m in messages if ts_re.search(m)]
        if not found:
            return "—"
        return f"{found[0]} → {found[-1]}"

    @staticmethod
    def _emoji_for(category: str) -> str:
        return {
            "timeout": "⏱️",
            "conexion": "🔌",
            "http_503": "🚫",
            "http_521": "🚫",
            "permisos": "🔒",
            "no_encontrado": "🔍",
            "base_datos": "💾",
            "nullpointer": "🪲",
            "otros": "⚠️",
        }.get(category, "⚠️")

    @staticmethod
    def _severity_emoji(sev: str) -> str:
        return {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢",
        }.get(str(sev).upper(), "⚪")

    # ------------------------------------------------------------------ #
    # Markdown
    # ------------------------------------------------------------------ #
    def _build_markdown(self, data: Dict[str, Any]) -> str:
        lines: List[str] = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        summary = data.get("summary", {})
        errors = data.get("errors", [])
        noise = data.get("noise_errors", [])
        by_category = data.get("by_category", {})
        ai = data.get("ai_analysis", {}) or {}
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
            "1. [Análisis con IA](#-análisis-con-ia)",
            "2. [Detalle de errores](#-detalle-de-errores)",
            "3. [Recomendaciones](#-recomendaciones)",
            "",
            "---",
            "",
        ]

        # ----- IA (formato estructurado nuevo) -----
        lines += self._build_ai_section(ai)

        # ----- Detalle de errores -----
        lines += ["## ⚠️ Detalle de errores", ""]
        if not errors:
            lines += ["✅ No se encontraron errores reales.", ""]
        else:
            for i, err in enumerate(errors[:30], 1):
                emoji = self._emoji_for(err.get("category", "otros"))
                count = err.get("error_count", err.get("unique_count", 0))
                cat = err.get("category", "otros")
                rng = self._extract_range(err.get("messages", []))

                lines += [
                    "<details>",
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
                lines += [f"_... y {len(errors) - 30} grupos más (ver HTML para el listado completo)._", ""]

        # ----- Ruido -----
        if noise:
            lines += [
                "## 🧹 Ruido filtrado (no son errores reales)",
                "",
                f"Se detectaron **{len(noise)}** grupos con HTML de páginas de error "
                "(Cloudflare, etc.). No se cuentan como errores de la aplicación.",
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

        lines += [
            "---",
            "",
            "_Reporte generado automáticamente por el Analizador de Logs con IA_",
        ]
        return "\n".join(lines)

    def _build_ai_section(self, ai: Dict[str, Any]) -> List[str]:
        """
        Genera la sección de IA en Markdown. Soporta dos formatos:
        - Nuevo (estructurado): resumen_ejecutivo, categorias, acciones_recomendadas...
        - Antiguo: {status, analysis}
        """
        lines: List[str] = ["## 🤖 Análisis con IA", ""]

        # ---- Caso de fallo ----
        status = ai.get("status", "")
        if status in ("failed", "error_parsing") or "error" in ai:
            lines.append(f"⚠️ **Estado:** {status or 'error'}")
            if ai.get("error"):
                lines.append(f"- Error: `{ai['error']}`")
            lines.append("")
            return lines

        # ---- Formato NUEVO estructurado ----
        if ai.get("resumen_ejecutivo") or ai.get("categorias"):
            sev = ai.get("severidad_global", "UNKNOWN")
            lines += [
                f"**Severidad global:** {self._severity_emoji(sev)} {sev}",
                "",
                "> **Resumen:** " + ai.get("resumen_ejecutivo", "—"),
                "",
            ]

            categorias = ai.get("categorias", []) or []
            if categorias:
                lines.append("### 🔍 Categorías de problemas")
                lines.append("")
                for i, cat in enumerate(categorias, 1):
                    sev_c = cat.get("severidad", "UNKNOWN")
                    lines += [
                        f"#### {i}. {cat.get('nombre', 'Sin nombre')}",
                        "",
                        f"- **Severidad:** {self._severity_emoji(sev_c)} {sev_c}",
                        f"- **Frecuencia:** {cat.get('frecuencia', 'N/A')}",
                        f"- **Descripción:** {cat.get('descripcion', 'N/A')}",
                        f"- **Causa probable:** {cat.get('causa_probable', 'N/A')}",
                    ]
                    if cat.get("evidencia"):
                        lines.append(f"- **Evidencia:** `{cat['evidencia']}`")
                    lines.append("")

            patrones = ai.get("patrones_clave", []) or []
            if patrones:
                lines.append("### 🎯 Patrones clave detectados")
                lines.append("")
                for p in patrones:
                    lines.append(f"- `{p}`")
                lines.append("")

            acciones = ai.get("acciones_recomendadas", []) or []
            if acciones:
                lines.append("### ✅ Acciones recomendadas")
                lines.append("")
                lines.append("| Prioridad | Acción | Razón |")
                lines.append("|---|---|---|")
                for acc in acciones:
                    prio = acc.get("prioridad", "MEDIA")
                    emoji = "🔴" if prio == "ALTA" else "🟡" if prio == "MEDIA" else "🟢"
                    accion = str(acc.get("accion", "N/A")).replace("|", "\\|")
                    razon = str(acc.get("razon", "N/A")).replace("|", "\\|")
                    lines.append(f"| {emoji} {prio} | {accion} | {razon} |")
                lines.append("")

            metricas = ai.get("metricas_sugeridas", []) or []
            if metricas:
                lines.append("### 📊 Métricas sugeridas")
                lines.append("")
                for m in metricas:
                    lines.append(f"- {m}")
                lines.append("")

            return lines

        # ---- Formato ANTIGUO (compatibilidad) ----
        if ai.get("analysis"):
            lines += [f"**Estado:** {status or 'success'}", "", str(ai["analysis"]), ""]
            return lines

        lines += ["⚠️ Análisis IA no disponible. Revisa que Ollama esté corriendo.", ""]
        return lines

    # ------------------------------------------------------------------ #
    # HTML (dashboard autocontenido)
    # ------------------------------------------------------------------ #
    def _build_html(self, data: Dict[str, Any]) -> str:
        summary = data.get("summary", {})
        errors = data.get("errors", [])
        noise = data.get("noise_errors", [])
        by_category = data.get("by_category", {})
        ai = data.get("ai_analysis", {}) or {}
        recommendations = data.get("recommendations", []) or []

        total_errors = summary.get("total_errors_real", summary.get("total_errors", 0))
        file_name = html.escape(str(data.get("file", "N/A")))
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cards = f"""
        <div class="cards">
          <div class="card"><div class="k">Logs</div><div class="v">{summary.get('total_logs', 0):,}</div></div>
          <div class="card"><div class="k">Transacciones</div><div class="v">{summary.get('total_groups', 0):,}</div></div>
          <div class="card danger"><div class="k">Errores reales</div><div class="v">{total_errors:,}</div></div>
          <div class="card muted"><div class="k">Ruido filtrado</div><div class="v">{summary.get('total_noise', 0):,}</div></div>
        </div>
        """

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

        noise_html = ""
        if noise:
            noise_html = f"""
            <h2>🧹 Ruido filtrado</h2>
            <p>{len(noise)} grupos de líneas tipo HTML/Cloudflare. No cuentan como errores de la app.</p>
            """

        rec_html = ""
        if recommendations:
            rec_html = "<h2>💡 Recomendaciones</h2><ul>" + \
                "".join(f"<li>{html.escape(str(r))}</li>" for r in recommendations) + "</ul>"

        # --- Sección IA en HTML (estructurada) ---
        ai_html = self._build_ai_html(ai)

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
  h3 {{ margin-top: 24px; color: var(--accent); }}
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
  .err-item .cat.timeout, .err-item .cat.conexion {{ background:#7c2d12; }}
  .err-item .cat.http_503, .err-item .cat.http_521 {{ background:#78350f; }}
  .err-item .cat.permisos {{ background:#581c87; }}
  .err-item .cat.nullpointer {{ background:#7f1d1d; }}
  .err-item .range {{ color: var(--muted); font-size: 12px; margin-left: auto; }}
  pre {{ background:#020617; padding:10px; border-radius:6px; overflow-x:auto;
         font-size: 12px; color:#cbd5e1; }}
  input.search {{ width:100%; padding:10px; border-radius:8px; border:1px solid #334155;
                  background:#020617; color: var(--fg); margin: 16px 0; }}
  .ai-box {{ background: var(--card); border-left: 4px solid var(--accent);
             padding: 16px 20px; border-radius: 8px; margin: 12px 0; }}
  .ai-summary {{ font-size: 16px; font-style: italic; color: #cbd5e1; margin: 8px 0 16px; }}
  .cat-block {{ background: #0b1220; border-radius: 8px; padding: 14px 16px;
                margin: 10px 0; border-left: 3px solid var(--accent); }}
  .cat-block h4 {{ margin: 0 0 8px; color: var(--accent); }}
  .cat-block p {{ margin: 4px 0; color: #cbd5e1; font-size: 14px; }}
  .sev {{ padding: 2px 8px; border-radius: 6px; font-size:12px; font-weight:600; }}
  .sev.CRITICAL {{ background:#7f1d1d; color:#fecaca; }}
  .sev.HIGH {{ background:#78350f; color:#fed7aa; }}
  .sev.MEDIUM {{ background:#713f12; color:#fde68a; }}
  .sev.LOW {{ background:#14532d; color:#bbf7d0; }}
  .actions-table {{ width:100%; border-collapse: collapse; margin-top: 8px; }}
  .actions-table th, .actions-table td {{ text-align:left; padding: 8px 10px;
      border-bottom: 1px solid #334155; font-size: 14px; }}
  .actions-table th {{ color: var(--muted); font-weight: 500; }}
  footer {{ margin-top: 40px; color: var(--muted); font-size: 12px; text-align:center; }}
</style>
</head>
<body>
  <h1>📊 Reporte de Análisis de Logs</h1>
  <div class="meta">📄 {file_name} · 🕒 {now}</div>

  {cards}

  <h2>🔝 Errores por tipo</h2>
  {bars_html or '<p>Sin errores clasificados.</p>'}

  {ai_html}

  {noise_html}

  <h2>⚠️ Detalle de errores</h2>
  <input class="search" id="q" placeholder="Buscar en los errores...">
  <div id="errs">{items_html or '<p>Sin errores reales.</p>'}</div>

  {rec_html}

  <footer>Reporte generado automáticamente por el Analizador de Logs con IA</footer>

<script>
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

    def _build_ai_html(self, ai: Dict[str, Any]) -> str:
        """Sección de IA en HTML con soporte para formato estructurado y antiguo."""
        status = ai.get("status", "")
        if status in ("failed", "error_parsing") or "error" in ai:
            return (
                "<h2>🤖 Análisis con IA</h2>"
                f"<p>⚠️ Estado: <b>{html.escape(str(status or 'error'))}</b></p>"
                f"<pre>{html.escape(str(ai.get('error', '')))}</pre>"
            )

        # Formato nuevo estructurado
        if ai.get("resumen_ejecutivo") or ai.get("categorias"):
            sev = html.escape(str(ai.get("severidad_global", "UNKNOWN")))
            out = [
                "<h2>🤖 Análisis con IA</h2>",
                '<div class="ai-box">',
                f'<p><b>Severidad global:</b> <span class="sev {sev}">{sev}</span></p>',
                f'<p class="ai-summary">{html.escape(str(ai.get("resumen_ejecutivo", "—")))}</p>',
            ]

            for i, cat in enumerate(ai.get("categorias", []), 1):
                sev_c = html.escape(str(cat.get("severidad", "UNKNOWN")))
                out.append('<div class="cat-block">')
                out.append(f'<h4>{i}. {html.escape(str(cat.get("nombre", "")))} '
                           f'<span class="sev {sev_c}">{sev_c}</span></h4>')
                out.append(f'<p><b>Frecuencia:</b> {html.escape(str(cat.get("frecuencia", "N/A")))}</p>')
                out.append(f'<p><b>Descripción:</b> {html.escape(str(cat.get("descripcion", "N/A")))}</p>')
                out.append(f'<p><b>Causa probable:</b> {html.escape(str(cat.get("causa_probable", "N/A")))}</p>')
                if cat.get("evidencia"):
                    out.append(f'<p><b>Evidencia:</b> <code>{html.escape(str(cat["evidencia"]))}</code></p>')
                out.append('</div>')

            patrones = ai.get("patrones_clave", []) or []
            if patrones:
                out.append("<h3>🎯 Patrones clave</h3><ul>")
                for p in patrones:
                    out.append(f"<li><code>{html.escape(str(p))}</code></li>")
                out.append("</ul>")

            acciones = ai.get("acciones_recomendadas", []) or []
            if acciones:
                out.append("<h3>✅ Acciones recomendadas</h3>")
                out.append('<table class="actions-table">'
                           '<thead><tr><th>Prioridad</th><th>Acción</th><th>Razón</th></tr></thead><tbody>')
                for acc in acciones:
                    prio = html.escape(str(acc.get("prioridad", "MEDIA")))
                    out.append(
                        f"<tr><td>{prio}</td>"
                        f"<td>{html.escape(str(acc.get('accion', '')))}</td>"
                        f"<td>{html.escape(str(acc.get('razon', '')))}</td></tr>"
                    )
                out.append("</tbody></table>")

            metricas = ai.get("metricas_sugeridas", []) or []
            if metricas:
                out.append("<h3>📊 Métricas sugeridas</h3><ul>")
                for m in metricas:
                    out.append(f"<li>{html.escape(str(m))}</li>")
                out.append("</ul>")

            out.append("</div>")
            return "".join(out)

        # Formato antiguo
        if ai.get("analysis"):
            return (
                "<h2>🤖 Análisis con IA</h2>"
                f"<p><b>Estado:</b> {html.escape(str(status or 'success'))}</p>"
                f"<div class='ai-box'>{html.escape(str(ai['analysis']))}</div>"
            )

        return "<h2>🤖 Análisis con IA</h2><p>No disponible.</p>"