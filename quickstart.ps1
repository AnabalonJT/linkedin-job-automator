# Quick Start Script - LinkedIn Job Automator (PowerShell)

Write-Host ""
Write-Host "🚀 LinkedIn Job Automator - Quick Start" -ForegroundColor Green
Write-Host "========================================"
Write-Host ""

# Activate venv
Write-Host "Activando virtual environment..." -ForegroundColor Cyan
& ".\venv\Scripts\Activate.ps1"

# Step 1: Validate setup
Write-Host "Validando setup..." -ForegroundColor Green
python scripts/validate_setup.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Validación fallida. Revisa la configuración." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================"
Write-Host ""

# Step 2: Ask what to do
Write-Host "¿Qué quieres hacer?" -ForegroundColor Cyan
Write-Host ""
Write-Host "1) Ejecutar scraper (buscar trabajos)"
Write-Host "2) Ejecutar applier (postular)"
Write-Host "3) Sincronizar con Google Sheets"
Write-Host "4) Ejecutar todo (scraper → applier → sheets)"
Write-Host "5) Levantar Docker (n8n + Selenium)"
Write-Host "6) Ver logs de Docker"
Write-Host ""

$choice = Read-Host "Selecciona opción (1-6)"

switch ($choice) {
    "1" {
        Write-Host "Iniciando scraper..." -ForegroundColor Green
        python scripts/linkedin_scraper.py
    }
    "2" {
        Write-Host "Iniciando applier..." -ForegroundColor Green
        python scripts/linkedin_applier.py
    }
    "3" {
        Write-Host "Sincronizando con Google Sheets..." -ForegroundColor Green
        python scripts/google_sheets_manager.py
    }
    "4" {
        Write-Host "Ejecutando todo (scraper → applier → sheets)..." -ForegroundColor Green
        Write-Host ""
        Write-Host "▶ Paso 1: Scraper" -ForegroundColor Yellow
        python scripts/linkedin_scraper.py
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "▶ Paso 2: Applier" -ForegroundColor Yellow
            python scripts/linkedin_applier.py
        } else {
            Write-Host "Scraper falló. Abortando." -ForegroundColor Red
            exit 1
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "▶ Paso 3: Google Sheets Sync" -ForegroundColor Yellow
            python scripts/google_sheets_manager.py
        } else {
            Write-Host "Applier falló. Abortando." -ForegroundColor Red
            exit 1
        }
    }
    "5" {
        Write-Host "Levantando Docker..." -ForegroundColor Green
        docker-compose up -d
        Write-Host ""
        Write-Host "Servicios levantados:" -ForegroundColor Green
        Write-Host "  n8n: http://localhost:5678" -ForegroundColor Cyan
        Write-Host "  Selenium Grid: http://localhost:4444" -ForegroundColor Cyan
        Write-Host "  Selenium VNC: localhost:7900 (password: secret)" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Verificando servicios..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        docker-compose ps
    }
    "6" {
        Write-Host "Mostrando logs de Docker..." -ForegroundColor Green
        docker-compose logs -f
    }
    default {
        Write-Host "Opción no válida" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "¡Listo!" -ForegroundColor Green
