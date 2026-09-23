#!/bin/bash
# scripts/setup.sh

echo "🚀 Configurando Log Analyzer App"
echo "================================"

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado"
    exit 1
fi

# Verificar Ollama
if ! command -v ollama &> /dev/null; then
    echo "⚠️  Ollama no está instalado"
    echo "   Visita https://ollama.ai para instalarlo"
fi

# Verificar Graphviz (para diagramas PNG)
if ! command -v dot &> /dev/null; then
    echo "⚠️  Graphviz no está instalado (necesario para diagramas PNG)"
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
        echo "   Instalando con winget..."
        winget install --id=Graphviz.Graphviz --silent --accept-source-agreements --accept-package-agreements 2>/dev/null || echo "   Ejecuta manualmente: winget install Graphviz.Graphviz"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "   Instala con: brew install graphviz"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "   Instala con: sudo apt-get install graphviz"
    fi
fi

# Instalar dependencias
echo "📦 Instalando dependencias..."
pip install -r requirements.txt

# Descargar modelo
if command -v ollama &> /dev/null; then
    echo "📥 Descargando modelo Qwen 2.5 Coder..."
    ollama pull qwen2.5-coder:1.5b
fi

# Crear directorios
echo "📁 Creando directorios necesarios..."
mkdir -p logs
mkdir -p output/reports

# Hacer ejecutables los scripts
chmod +x scripts/*.sh

echo ""
echo "✅ Setup completado"
echo ""
echo "📝 Próximos pasos:"
echo "   1. Coloca tu archivo de log en la carpeta logs/"
echo "   2. Ejecuta: ./scripts/run_analysis.sh logs/tu-archivo.log"
echo "   3. Revisa el reporte en output/reports/"