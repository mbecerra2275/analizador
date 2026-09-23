# scripts/setup.ps1
# Script de configuración para Windows (PowerShell)

Write-Host "🚀 Configurando Log Analyzer App" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

# Verificar Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python no está instalado" -ForegroundColor Red
    Write-Host "   Instala desde https://python.org o usa: winget install Python.Python.3.11" -ForegroundColor Yellow
    exit 1
}

# Verificar Ollama
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "⚠️  Ollama no está instalado" -ForegroundColor Yellow
    Write-Host "   Visita https://ollama.ai para instalarlo" -ForegroundColor Yellow
    Write-Host "   O instala con: winget install Ollama.Ollama" -ForegroundColor Yellow
}

# Verificar Graphviz (para diagramas PNG)
if (-not (Get-Command dot -ErrorAction SilentlyContinue)) {
    Write-Host "⚠️  Graphviz no está instalado (necesario para diagramas PNG)" -ForegroundColor Yellow
    Write-Host "   Instalando con winget..." -ForegroundColor Cyan
    $exitCode = winget install --id=Graphviz.Graphviz --silent --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Graphviz instalado" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Error instalando Graphviz. Ejecuta manualmente:" -ForegroundColor Red
        Write-Host "      winget install Graphviz.Graphviz" -ForegroundColor Yellow
    }
}

# Instalar dependencias Python
Write-Host "📦 Instalando dependencias Python..." -ForegroundColor Cyan
pip install -r requirements.txt

# Descargar modelo Ollama
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host "📥 Descargando modelo Qwen 2.5 Coder..." -ForegroundColor Cyan
    ollama pull qwen2.5-coder:1.5b
}

# Crear directorios
Write-Host "📁 Creando directorios necesarios..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path logs, output/reports | Out-Null

Write-Host ""
Write-Host "✅ Setup completado" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Próximos pasos:" -ForegroundColor Cyan
Write-Host "   1. Coloca tu archivo de log en la carpeta logs/" -ForegroundColor White
Write-Host "   2. Ejecuta: python -m app.cli --file logs/tu-archivo.log" -ForegroundColor White
Write-Host "   3. Revisa el reporte en output/reports/" -ForegroundColor White
Write-Host "   4. O usa la GUI: python -m app.cli --gui" -ForegroundColor White