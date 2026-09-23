# 📊 Log Analyzer IA - Guía Rápida

## 🚀 Instalación (Solo la primera vez)

1. **Descargue** `LogAnalyzer_Setup_v1.0.0.exe`
2. **Doble clic** → Siguiente → Siguiente → Instalar
3. **Espere** a que termine (descarga ~1.5 GB modelo IA)
4. **Finalizar** → Se abre automáticamente

---

## 🎯 Uso Básico (3 pasos)

```
┌─────────────────────────────────────┐
│  1. 📂 Examinar...   → Seleccione su archivo .log    │
│  2. 🚀 Iniciar Análisis                │
│  3. 📄 Ver reporte (se abre solo)      │
└─────────────────────────────────────┘
```

### Formatos soportados
- `.log` (estándar)
- `.txt` (texto plano)
- Formato Kubernetes/Skooner
- Formato: `info: correlation_id timestamp mensaje +duracion`

---

## 📋 Qué genera

| Archivo | Qué contiene |
|---------|--------------|
| `analysis_report_*.html` | **Reporte visual** (ábralo en navegador) |
| `analysis_report_*.md` | Fuente en Markdown |

El reporte incluye:
- ✅ Resumen ejecutivo (logs, transacciones, errores)
- 🤖 Análisis con IA (top 3 problemas + recomendaciones)
- ⚠️ Errores detallados agrupados por correlation ID
- 💡 Recomendaciones prácticas

---

## 🤖 Para que funcione la IA

**Obligatorio:** Ollama corriendo en segundo plano

```cmd
# Una sola vez (si no se instaló automáticamente):
ollama serve
```

Mantenga esa ventana abierta mientras usa Log Analyzer.

### Modelos disponibles
| Modelo | Uso | Tamaño |
|--------|-----|--------|
| `qwen2.5-coder:1.5b` | Por defecto (rápido) | 1.5 GB |
| `llama3.2:3b` | Más preciso | 3 GB |
| `phi3:mini` | Muy rápido | 2 GB |

Cambiar modelo: Edite `config.yaml` → `ollama_model`

---

## 🔧 Solución de Problemas

| Problema | Solución |
|----------|----------|
| "Ollama no disponible" | Abra cmd → `ollama serve` (deje abierto) |
| "Modelo no encontrado" | `ollama pull qwen2.5-coder:1.5b` |
| "Graphviz no encontrado" | Reinstale → marque "Instalar Graphviz" |
| Error "Permiso denegado" | Ejecute como Administrador |
| Reporte no abre | Doble clic en `.html` en `output/reports/` |

---

## 📁 Dónde están los reportes

```
C:\Users\SU_USUARIO\AppData\Local\LogAnalyzer\output\reports\
```

O use el botón **📄 Abrir Reporte** en la aplicación.

---

## 🔒 Privacidad

- **100% Local**: Nada sale de su máquina
- **Ollama** corre en `localhost:11434`
- **Sin telemetría**, sin tracking, sin cuentas

---

## 📞 Soporte

- **Logs de la app**: `logs/analyzer.log`
- **Issues**: GitHub Issues
- **Email**: soporte@ejemplo.com

---

**Versión 1.0** | Windows 10/11 | Requiere 4 GB RAM + 3 GB disco