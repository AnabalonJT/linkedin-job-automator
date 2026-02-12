#!/bin/bash
# Quick Start Script - LinkedIn Job Automator

echo ""
echo "🚀 LinkedIn Job Automator - Quick Start"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_step() {
    echo -e "${GREEN}➜${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Step 1: Validate setup
print_step "Validando setup..."
python scripts/validate_setup.py

if [ $? -ne 0 ]; then
    print_error "Validación fallida. Revisa la configuración."
    exit 1
fi

echo ""
echo "========================================"
echo ""

# Step 2: Ask what to do
echo "¿Qué quieres hacer?"
echo ""
echo "1) Ejecutar scraper (buscar trabajos)"
echo "2) Ejecutar applier (postular)"
echo "3) Sincronizar con Google Sheets"
echo "4) Ejecutar todo (scraper → applier → sheets)"
echo "5) Levantar Docker (n8n + Selenium)"
echo "6) Ver logs de Docker"
echo ""
read -p "Selecciona opción (1-6): " choice

case $choice in
    1)
        print_step "Iniciando scraper..."
        python scripts/linkedin_scraper.py
        ;;
    2)
        print_step "Iniciando applier..."
        python scripts/linkedin_applier.py
        ;;
    3)
        print_step "Sincronizando con Google Sheets..."
        python scripts/google_sheets_manager.py
        ;;
    4)
        print_step "Ejecutando todo (scraper → applier → sheets)..."
        python scripts/linkedin_scraper.py
        if [ $? -eq 0 ]; then
            python scripts/linkedin_applier.py
        fi
        if [ $? -eq 0 ]; then
            python scripts/google_sheets_manager.py
        fi
        ;;
    5)
        print_step "Levantando Docker..."
        docker-compose up -d
        echo ""
        echo "n8n disponible en: http://localhost:5678"
        echo "Selenium Grid en: http://localhost:4444"
        echo "VNC (debug Chrome) en: localhost:7900 (password: secret)"
        ;;
    6)
        print_step "Mostrando logs de Docker..."
        docker-compose logs -f
        ;;
    *)
        print_error "Opción no válida"
        exit 1
        ;;
esac

echo ""
print_step "¡Listo!"
