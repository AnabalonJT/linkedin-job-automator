#!/usr/bin/env python3
"""
Utilidades compartidas para LinkedIn Job Automator
Funciones auxiliares para cargar configuración, credenciales, etc.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import sys

# Importar el gestor de credenciales
sys.path.append(str(Path(__file__).parent))
from credentials_manager import CredentialsManager


class Config:
    """Clase para manejar configuración del proyecto"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.project_root = Path(__file__).parent.parent
        
        # Cargar variables de entorno
        load_dotenv(self.project_root / ".env")
        
    def load_yaml_config(self, filename: str = "config.yaml") -> Dict[str, Any]:
        """Carga archivo de configuración YAML"""
        config_file = self.config_dir / filename
        
        if not config_file.exists():
            raise FileNotFoundError(f"Archivo de configuración no encontrado: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def load_json_config(self, filename: str) -> Dict[str, Any]:
        """Carga archivo de configuración JSON"""
        config_file = self.config_dir / filename
        
        if not config_file.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_linkedin_credentials(self, password: str = None) -> Optional[Dict[str, str]]:
        """Obtiene credenciales de LinkedIn encriptadas
        
        Si no se proporciona contraseña, intenta desde LINKEDIN_MASTER_PASSWORD env var
        """
        manager = CredentialsManager(str(self.config_dir))
        
        # Si no hay password, intentar desde env (para Docker)
        if password is None:
            password = os.getenv('LINKEDIN_MASTER_PASSWORD')
        
        credentials = manager.load_credentials(password)
        
        if credentials and 'linkedin' in credentials:
            return credentials['linkedin']
        
        return None
    
    def get_env_var(self, key: str, default: Any = None) -> Any:
        """Obtiene variable de entorno"""
        return os.getenv(key, default)
    
    def get_google_sheets_id(self) -> str:
        """Obtiene ID de Google Sheets"""
        sheets_id = self.get_env_var('GOOGLE_SHEETS_ID')
        if not sheets_id:
            raise ValueError("GOOGLE_SHEETS_ID no configurado en .env")
        return sheets_id
    
    def get_telegram_config(self) -> Dict[str, str]:
        """Obtiene configuración de Telegram"""
        return {
            'bot_token': self.get_env_var('TELEGRAM_BOT_TOKEN'),
            'chat_id': self.get_env_var('TELEGRAM_CHAT_ID')
        }
    
    def get_cv_paths(self) -> Dict[str, str]:
        """Obtiene rutas de los CVs"""
        config = self.load_yaml_config()
        cvs = config.get('cvs', {})
        
        cv_paths = {}
        for cv_type, cv_info in cvs.items():
            path = cv_info.get('path', '')
            # Convertir ruta relativa a absoluta
            if path.startswith('/config/'):
                path = str(self.config_dir / path.replace('/config/', ''))
            cv_paths[cv_type] = path
        
        return cv_paths


class Logger:
    """Sistema simple de logging"""
    
    def __init__(self, log_dir: str = "data/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"execution_{timestamp}.log"
    
    def log(self, message: str, level: str = "INFO"):
        """Registra un mensaje"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # Imprimir en consola
        print(log_entry)
        
        # Guardar en archivo
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    
    def info(self, message: str):
        """Log nivel INFO"""
        self.log(message, "INFO")
    
    def error(self, message: str):
        """Log nivel ERROR"""
        self.log(message, "ERROR")
    
    def warning(self, message: str):
        """Log nivel WARNING"""
        self.log(message, "WARNING")
    
    def success(self, message: str):
        """Log nivel SUCCESS"""
        self.log(message, "SUCCESS")
    
    def debug(self, message: str):
        """Log nivel DEBUG (mismo que INFO pero para detalles)"""
        self.log(message, "DEBUG")


def select_cv_by_keywords(job_title: str, job_description: str, config: Config) -> str:
    """
    Selecciona el CV apropiado basándose en keywords del trabajo
    
    Args:
        job_title: Título del trabajo
        job_description: Descripción del trabajo
        config: Objeto de configuración
    
    Returns:
        Tipo de CV a usar ('software' o 'consultoria')
    """
    yaml_config = config.load_yaml_config()
    cv_config = yaml_config.get('cvs', {})
    
    text_to_analyze = (job_title + " " + job_description).lower()
    
    # ============================================================================
    # PASO 1: Palabras clave DEFINITIVAS (prioridad alta)
    # ============================================================================
    
    # Si contiene "automatización" o "automatizacion", usar consultoria
    if "automatización" in text_to_analyze or "automatizacion" in text_to_analyze:
        return "consultoria"

    
    # Si contiene "data engineer" completo, usar consultoria (más específico que solo "engineer")
    if "data engineer" in text_to_analyze:
        return "consultoria"
    
    # Si contiene "machine learning" o "ml", usar consultoria
    if "machine learning" in text_to_analyze or " ml " in text_to_analyze:
        return "consultoria"
    
    # Si contiene "business intelligence" o "bi", usar consultoria
    if "business intelligence" in text_to_analyze or " bi " in text_to_analyze:
        return "consultoria"
    
    # Si contiene "data analyst" o "analytics", usar consultoria
    if "data analyst" in text_to_analyze or "analytics" in text_to_analyze:
        return "consultoria"
    
    # ============================================================================
    # PASO 2: Scoring por keywords si no hay coincidencia definitiva
    # ============================================================================
    
    scores = {}
    for cv_type, cv_info in cv_config.items():
        keywords = cv_info.get('keywords', [])
        score = sum(1 for keyword in keywords if keyword.lower() in text_to_analyze)
        scores[cv_type] = score
    
    # Retornar el CV con mayor score
    if scores:
        selected_cv = max(scores, key=scores.get)
        
        # Si hay empate o score muy bajo, usar default
        if scores[selected_cv] == 0:
            return yaml_config.get('seleccion_cv', {}).get('cv_por_defecto', 'software')
        
        return selected_cv
    
    return 'software'  # Default


def format_job_data(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formatea datos del trabajo para guardar en Google Sheets
    
    Args:
        job_data: Diccionario con datos del trabajo
    
    Returns:
        Diccionario formateado
    """
    from datetime import datetime
    
    return {
        'fecha_aplicacion': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'empresa': job_data.get('company', 'N/A'),
        'puesto': job_data.get('title', 'N/A'),
        'url': job_data.get('url', 'N/A'),
        'ubicacion': job_data.get('location', 'N/A'),
        'tipo_aplicacion': job_data.get('application_type', 'MANUAL'),
        'cv_usado': job_data.get('cv_used', 'N/A'),
        'estado': job_data.get('status', 'PENDIENTE'),
        'ultimo_update': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'notas': job_data.get('notes', ''),
        'pruebas_pendientes': job_data.get('has_tests', False)
    }


def send_telegram_notification(message: str, config: Config):
    """
    Envía notificación por Telegram
    
    Args:
        message: Mensaje a enviar
        config: Objeto de configuración
    """
    import requests
    
    telegram_config = config.get_telegram_config()
    bot_token = telegram_config.get('bot_token')
    chat_id = telegram_config.get('chat_id')
    
    if not bot_token or not chat_id:
        print("⚠️  Configuración de Telegram incompleta, saltando notificación")
        return
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Notificación enviada por Telegram")
        else:
            print(f"⚠️  Error enviando notificación: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Error enviando notificación: {str(e)}")


def is_job_already_applied(job_url: str, applied_jobs: list) -> bool:
    """
    Verifica si ya se aplicó a un trabajo
    
    Args:
        job_url: URL del trabajo
        applied_jobs: Lista de trabajos ya aplicados
    
    Returns:
        True si ya se aplicó, False si no
    """
    return job_url in applied_jobs


def extract_job_id_from_url(url: str) -> str:
    """
    Extrae el ID único del trabajo desde la URL de LinkedIn
    
    Args:
        url: URL del trabajo de LinkedIn
    
    Returns:
        Job ID (ej: "4346887275")
    """
    import re
    
    # Buscar patrón /jobs/view/NÚMEROS/
    match = re.search(r'/jobs/view/(\d+)', url)
    if match:
        return match.group(1)
    
    # Si no encuentra, retornar la URL completa (fallback)
    return url


def should_skip_job(job_title: str, job_description: str, config: Config) -> bool:
    """
    Verifica si un trabajo debe ser omitido basándose en keywords excluidas
    
    Args:
        job_title: Título del trabajo
        job_description: Descripción del trabajo
        config: Objeto de configuración
    
    Returns:
        True si debe omitirse, False si debe procesarse
    """
    yaml_config = config.load_yaml_config()
    excluded_keywords = yaml_config.get('busqueda', {}).get('palabras_excluidas', [])
    
    text_to_check = (job_title + " " + job_description).lower()
    
    for keyword in excluded_keywords:
        if keyword.lower() in text_to_check:
            return True
    
    return False


def clean_text(text: str) -> str:
    """Limpia texto removiendo caracteres especiales y espacios extra"""
    if not text:
        return ""
    
    # Remover espacios extra
    text = ' '.join(text.split())
    
    # Remover caracteres problemáticos
    text = text.replace('\n', ' ').replace('\r', ' ')
    
    return text.strip()


def validate_config_files(config_dir: str = "config") -> bool:
    """
    Valida que todos los archivos de configuración necesarios existan
    
    Returns:
        True si todo está OK, False si falta algo
    """
    config_path = Path(config_dir)
    required_files = [
        'config.yaml',
        'respuestas_comunes.json',
        'credentials.enc',
        '.key'
    ]
    
    missing_files = []
    for filename in required_files:
        if not (config_path / filename).exists():
            missing_files.append(filename)
    
    if missing_files:
        print(f"❌ Archivos faltantes en /config/: {', '.join(missing_files)}")
        return False
    
    print("✅ Todos los archivos de configuración presentes")
    return True


if __name__ == "__main__":
    # Testing
    print("🧪 Probando utilidades...")
    
    # Validar archivos
    validate_config_files()
    
    # Probar carga de config
    config = Config()
    
    print("\n📋 Configuración YAML:")
    yaml_config = config.load_yaml_config()
    print(f"  - Palabras clave de búsqueda: {len(yaml_config['busqueda']['palabras_clave'])}")
    print(f"  - Ubicaciones: {len(yaml_config['busqueda']['ubicaciones'])}")
    
    print("\n📋 Configuración JSON (respuestas):")
    json_config = config.load_json_config('respuestas_comunes.json')
    print(f"  - Preguntas configuradas: {len(json_config['preguntas_configuradas'])}")
    
    print("\n🔐 Credenciales de LinkedIn:")
    creds = config.get_linkedin_credentials()
    if creds:
        print(f"  ✅ Email: {creds['username']}")
        print(f"  ✅ Password: {'*' * len(creds['password'])}")
    else:
        print("  ❌ No se pudieron cargar las credenciales")
    
    print("\n📱 Configuración de Telegram:")
    telegram = config.get_telegram_config()
    if telegram['bot_token']:
        print(f"  ✅ Bot Token: {telegram['bot_token'][:20]}...")
        print(f"  ✅ Chat ID: {telegram['chat_id']}")
    else:
        print("  ⚠️  Telegram no configurado")
    
    print("\n✅ Pruebas completadas")