#!/bin/bash
# scripts/run_analysis.sh

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Iniciando Análisis de Logs${NC}"
echo "================================================"

# Configuración
LOG_FILE=${1:-"logs/sample.log"}
OUTPUT_DIR=${2:-"output/reports"}
CONFIG_FILE=${3:-"config/default.yaml"}

# Verificar que existe el archivo de log
if [ ! -f "$LOG_FILE" ]; then
    echo -e "${RED}❌ Error: Archivo de log no encontrado: $LOG_FILE${NC}"
    echo "Uso: ./scripts/run_analysis.sh [archivo.log] [output_dir] [config.yaml]"
    exit 1
fi

# Crear directorios necesarios
mkdir -p "$OUTPUT_DIR"
mkdir -p output/temp

echo -e "${YELLOW}📂 Archivo:${NC} $LOG_FILE"
echo -e "${YELLOW}📄 Salida:${NC} $OUTPUT_DIR"
echo -e "${YELLOW}⚙️  Configuración:${NC} $CONFIG_FILE"
echo ""

# Ejecutar el análisis
echo -e "${GREEN}▶️  Ejecutando análisis...${NC}"
python -m app.cli \
    --file "$LOG_FILE" \
    --output "$OUTPUT_DIR" \
    --config "$CONFIG_FILE" \
    --verbose

# Verificar resultado
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Análisis completado exitosamente${NC}"
    
    # Buscar el reporte más reciente
    LATEST_REPORT=$(ls -t "$OUTPUT_DIR"/*.md 2>/dev/null | head -1)
    if [ -n "$LATEST_REPORT" ]; then
        echo ""
        echo -e "${YELLOW}📄 Reporte generado:${NC} $LATEST_REPORT"
        
        # Intentar abrir el archivo
        if [[ "$OSTYPE" == "darwin"* ]]; then
            open "$LATEST_REPORT"
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            if command -v xdg-open &> /dev/null; then
                xdg-open "$LATEST_REPORT" 2>/dev/null || echo "  (No se pudo abrir automáticamente)"
            fi
        fi
    fi
else
    echo -e "${RED}❌ Error durante el análisis${NC}"
    exit 1
fi

echo "================================================"