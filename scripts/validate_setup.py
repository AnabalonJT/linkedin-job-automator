#!/usr/bin/env python3
"""
Quick Validation Script
Valida que todas las dependencias y configuraciones estén correctas
"""

import os
import sys
from pathlib import Path
import json

def print_status(status: str, message: str):
    """Print colored status message"""
    if status == "✓":
        print(f"✅ {message}")
    elif status == "✗":
        print(f"❌ {message}")
    elif status == "⚠":
        print(f"⚠️  {message}")
    elif status == "ℹ":
        print(f"ℹ️  {message}")

def check_environment():
    """Check environment and dependencies"""
    print("\n📋 Validación de Ambiente")
    print("=" * 60)
    
    # Python version
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    if sys.version_info >= (3, 8):
        print_status("✓", f"Python {version}")
    else:
        print_status("✗", f"Python {version} (requiere 3.8+)")
        return False
    
    # Check venv
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print_status("✓", "Virtual environment activo")
    else:
        print_status("⚠", "Virtual environment no detectado (activar: venv\\Scripts\\Activate.ps1)")
    
    # Check required packages
    required_packages = [
        'selenium', 'gspread', 'google', 'requests', 'pyyaml', 'cryptography', 'python-dotenv'
    ]
    
    for pkg in required_packages:
        try:
            __import__(pkg)
            print_status("✓", f"Paquete {pkg} instalado")
        except ImportError:
            print_status("✗", f"Paquete {pkg} NO instalado")
            return False
    
    return True

def check_configuration():
    """Check configuration files"""
    print("\n⚙️  Validación de Configuración")
    print("=" * 60)
    
    success = True
    
    # Check .env
    if Path('.env').exists():
        print_status("✓", "Archivo .env encontrado")
        try:
            with open('.env', 'r') as f:
                env_content = f.read()
                if 'GOOGLE_SHEETS_ID' in env_content:
                    print_status("✓", "GOOGLE_SHEETS_ID configurado")
                else:
                    print_status("⚠", "GOOGLE_SHEETS_ID no configurado")
                
                if 'TELEGRAM_BOT_TOKEN' in env_content:
                    print_status("✓", "TELEGRAM_BOT_TOKEN configurado")
                else:
                    print_status("⚠", "TELEGRAM_BOT_TOKEN no configurado (opcional)")
                
                if 'TELEGRAM_CHAT_ID' in env_content:
                    print_status("✓", "TELEGRAM_CHAT_ID configurado")
                else:
                    print_status("⚠", "TELEGRAM_CHAT_ID no configurado (opcional)")
        except Exception as e:
            print_status("✗", f"Error leyendo .env: {e}")
            success = False
    else:
        print_status("✗", "Archivo .env NO encontrado")
        success = False
    
    # Check config files
    config_files = [
        ('config/google_credentials.json', 'Google Sheets credentials'),
        ('config/config.yaml', 'Configuración de búsqueda'),
        ('config/respuestas_comunes.json', 'Respuestas automáticas'),
    ]
    
    for file_path, description in config_files:
        if Path(file_path).exists():
            print_status("✓", f"{description} ({file_path})")
        else:
            print_status("⚠", f"{description} NO encontrado ({file_path})")
    
    # Check data directories
    dirs = [
        'data/logs',
        'data/cookies',
    ]
    
    for dir_path in dirs:
        if Path(dir_path).exists():
            print_status("✓", f"Directorio {dir_path} existe")
        else:
            print_status("⚠", f"Directorio {dir_path} NO existe (se creará automáticamente)")
    
    return success

def check_scripts():
    """Check if all scripts exist"""
    print("\n📝 Validación de Scripts")
    print("=" * 60)
    
    scripts = [
        'scripts/linkedin_scraper.py',
        'scripts/linkedin_applier.py',
        'scripts/google_sheets_manager.py',
        'scripts/telegram_notifier.py',
        'scripts/credentials_manager.py',
        'scripts/utils.py',
    ]
    
    for script in scripts:
        if Path(script).exists():
            print_status("✓", script)
        else:
            print_status("✗", f"{script} NO encontrado")
            return False
    
    return True

def check_docker():
    """Check if Docker is available"""
    print("\n🐳 Validación de Docker")
    print("=" * 60)
    
    try:
        import subprocess
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print_status("✓", f"Docker: {result.stdout.strip()}")
        else:
            print_status("✗", "Docker no responde")
            return False
        
        result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print_status("✓", f"Docker Compose: {result.stdout.strip()}")
        else:
            print_status("✗", "Docker Compose no responde")
            return False
        
        return True
    except FileNotFoundError:
        print_status("⚠", "Docker no encontrado en PATH (necesario para n8n)")
        return False

def check_connectivity():
    """Check connectivity to services"""
    print("\n🌐 Validación de Conectividad")
    print("=" * 60)
    
    try:
        # Test Google Sheets
        try:
            from scripts.google_sheets_manager import GoogleSheetsManager
            from utils import Config
            
            config = Config()
            sheets_id = config.get_env_var('GOOGLE_SHEETS_ID')
            
            if sheets_id and Path('config/google_credentials.json').exists():
                try:
                    manager = GoogleSheetsManager('config/google_credentials.json', sheets_id)
                    print_status("✓", "Google Sheets conectado")
                except Exception as e:
                    print_status("✗", f"Google Sheets error: {str(e)[:50]}")
            else:
                print_status("⚠", "Google Sheets no configurado")
        except Exception as e:
            print_status("⚠", f"No se pudo validar Google Sheets: {e}")
        
        # Test Telegram
        try:
            from scripts.telegram_notifier import TelegramNotifier
            try:
                notifier = TelegramNotifier()
                print_status("✓", "Telegram configurado")
            except ValueError:
                print_status("⚠", "Telegram no configurado (opcional)")
        except Exception as e:
            print_status("⚠", f"No se pudo validar Telegram: {e}")
        
    except Exception as e:
        print_status("⚠", f"Error en validación de conectividad: {e}")

def main():
    """Main validation"""
    print("\n" + "=" * 60)
    print("🧪 VALIDACIÓN DE LINKEDIN JOB AUTOMATOR")
    print("=" * 60)
    
    # Change to project directory
    os.chdir(Path(__file__).parent)
    
    checks = [
        ("Ambiente", check_environment),
        ("Configuración", check_configuration),
        ("Scripts", check_scripts),
        ("Docker", check_docker),
        ("Conectividad", check_connectivity),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print_status("✗", f"Error en {name}: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 RESUMEN")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nValidaciones pasadas: {passed}/{total}")
    
    if passed == total:
        print_status("✓", "¡Todas las validaciones pasaron! Listo para ejecutar.")
        print("\nProximos pasos:")
        print("  1. docker-compose up -d  (para levantar n8n)")
        print("  2. python scripts/linkedin_scraper.py  (test manual)")
        print("  3. python scripts/linkedin_applier.py  (test manual)")
        print("  4. http://localhost:5678  (n8n workflow)")
        return 0
    else:
        print_status("✗", "Algunas validaciones fallaron. Ver arriba para detalles.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
