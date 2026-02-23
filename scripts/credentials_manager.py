#!/usr/bin/env python3
"""
Sistema de Gestión Segura de Credenciales para LinkedIn Automator
Encripta y almacena credenciales de forma segura usando Fernet (criptografía simétrica)
"""

import os
import json
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from getpass import getpass
import sys


class CredentialsManager:
    """Gestor de credenciales encriptadas"""
    
    def __init__(self, config_dir="config"):
        self.config_dir = Path(config_dir)
        self.credentials_file = self.config_dir / "credentials.enc"
        self.key_file = self.config_dir / ".key"
        
        # Crear directorio si no existe
        self.config_dir.mkdir(exist_ok=True)
        
    def _generate_key(self, password: str, salt: bytes = None) -> tuple:
        """Genera una clave de encriptación desde una contraseña"""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    def setup_master_password(self):
        """Configura la contraseña maestra por primera vez"""
        print("\n🔐 Configuración de contraseña maestra")
        print("=" * 50)
        print("Esta contraseña se usará para encriptar tus credenciales.")
        print("⚠️  IMPORTANTE: NO PIERDAS ESTA CONTRASEÑA")
        print("=" * 50)
        
        while True:
            password = getpass("\nIngresa una contraseña maestra: ")
            confirm = getpass("Confirma la contraseña: ")
            
            if password != confirm:
                print("❌ Las contraseñas no coinciden. Intenta nuevamente.")
                continue
            
            if len(password) < 8:
                print("❌ La contraseña debe tener al menos 8 caracteres.")
                continue
            
            break
        
        # Generar clave y guardar salt
        key, salt = self._generate_key(password)
        
        with open(self.key_file, 'wb') as f:
            f.write(salt)
        
        print("\n✅ Contraseña maestra configurada exitosamente")
        return key
    
    def get_key(self, password: str = None) -> bytes:
        """Obtiene la clave de encriptación"""
        if not self.key_file.exists():
            return self.setup_master_password()
        
        # Leer salt
        with open(self.key_file, 'rb') as f:
            salt = f.read()
        
        if password is None:
            # Intentar obtener de variable de entorno (para Docker)
            password = os.getenv('LINKEDIN_MASTER_PASSWORD')
            
            if password is None:
                # Si no está en env, solicitar interactivamente
                password = getpass("\n🔑 Ingresa tu contraseña maestra: ")
        
        key, _ = self._generate_key(password, salt)
        return key
    
    def save_credentials(self, credentials: dict):
        """Guarda credenciales encriptadas"""
        try:
            key = self.get_key()
            fernet = Fernet(key)
            
            # Convertir a JSON y encriptar
            json_data = json.dumps(credentials, indent=2)
            encrypted_data = fernet.encrypt(json_data.encode())
            
            # Guardar
            with open(self.credentials_file, 'wb') as f:
                f.write(encrypted_data)
            
            print("\n✅ Credenciales guardadas de forma segura")
            return True
            
        except Exception as e:
            print(f"\n❌ Error guardando credenciales: {str(e)}")
            return False
    
    def load_credentials(self, password: str = None) -> dict:
        """Carga credenciales encriptadas"""
        if not self.credentials_file.exists():
            print("⚠️  No hay credenciales guardadas")
            return None
        
        try:
            key = self.get_key(password)
            fernet = Fernet(key)
            
            # Leer y desencriptar
            with open(self.credentials_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = fernet.decrypt(encrypted_data)
            credentials = json.loads(decrypted_data.decode())
            
            return credentials
            
        except Exception as e:
            print(f"\n❌ Error cargando credenciales: {str(e)}")
            print("Verifica que la contraseña sea correcta.")
            return None
    
    def update_credentials(self, service: str, username: str, password: str):
        """Actualiza credenciales de un servicio específico"""
        credentials = self.load_credentials()
        
        if credentials is None:
            credentials = {}
        
        credentials[service] = {
            "username": username,
            "password": password
        }
        
        return self.save_credentials(credentials)
    
    def delete_credentials(self):
        """Elimina todas las credenciales"""
        if self.credentials_file.exists():
            self.credentials_file.unlink()
        if self.key_file.exists():
            self.key_file.unlink()
        print("✅ Credenciales eliminadas")


def setup_linkedin_credentials():
    """Wizard para configurar credenciales de LinkedIn"""
    print("\n" + "=" * 60)
    print("🔧 CONFIGURACIÓN DE CREDENCIALES DE LINKEDIN")
    print("=" * 60)
    
    manager = CredentialsManager()
    
    # Verificar si ya existen credenciales
    existing = manager.load_credentials()
    if existing and 'linkedin' in existing:
        print("\n⚠️  Ya tienes credenciales de LinkedIn guardadas.")
        overwrite = input("¿Deseas sobrescribirlas? (s/n): ").lower()
        if overwrite != 's':
            print("Operación cancelada.")
            return
    
    print("\n📝 Ingresa tus credenciales de LinkedIn:")
    print("(Estas se guardarán encriptadas localmente)")
    
    linkedin_email = input("\nEmail de LinkedIn: ").strip()
    linkedin_password = getpass("Contraseña de LinkedIn: ")
    
    # Confirmar
    print("\n" + "-" * 60)
    print(f"Email: {linkedin_email}")
    print(f"Contraseña: {'*' * len(linkedin_password)}")
    print("-" * 60)
    
    confirm = input("\n¿Los datos son correctos? (s/n): ").lower()
    if confirm != 's':
        print("Operación cancelada.")
        return
    
    # Guardar
    success = manager.update_credentials(
        service="linkedin",
        username=linkedin_email,
        password=linkedin_password
    )
    
    if success:
        print("\n" + "=" * 60)
        print("✅ CREDENCIALES DE LINKEDIN CONFIGURADAS EXITOSAMENTE")
        print("=" * 60)
        print("\n🔒 Tus credenciales están encriptadas y seguras.")
        print("💡 El bot las usará automáticamente cuando sea necesario.")


def setup_openrouter_credentials():
    """Configurar API key de OpenRouter para IA"""
    print("\n" + "=" * 60)
    print("🤖 CONFIGURACIÓN DE OPENROUTER (IA)")
    print("=" * 60)
    
    manager = CredentialsManager()
    
    print("\n📝 OpenRouter es el proveedor de IA (Llama-3.3-70B)")
    print("Obtén tu API key en: https://openrouter.ai/keys")
    
    api_key = getpass("\nOpenRouter API Key (sk-or-...): ").strip()
    
    if not api_key:
        print("❌ API key no puede estar vacía")
        return
    
    confirm = input("\n¿Estás seguro? (s/n): ").lower()
    if confirm != 's':
        return
    
    credentials = manager.load_credentials() or {}
    credentials['openrouter'] = {"api_key": api_key}
    
    if manager.save_credentials(credentials):
        print("\n✅ OpenRouter API key guardada exitosamente")
        # Actualizar .env
        _update_env_file('OPENROUTER_API_KEY', api_key)


def setup_cv_paths():
    """Configurar rutas de CVs duales"""
    print("\n" + "=" * 60)
    print("📄 CONFIGURACIÓN DE CVs (SISTEMA DUAL)")
    print("=" * 60)
    
    manager = CredentialsManager()
    
    print("\n📝 Ingresa las rutas de tus CVs:")
    print("(Formato: config/archivo.pdf)")
    
    cv_software = input("\nRuta CV Software Engineer (ej: config/CV Software Engineer.pdf): ").strip()
    cv_data = input("Ruta CV Data Scientist/Ingeniero (ej: config/CV Data.pdf): ").strip()
    
    if not cv_software or not cv_data:
        print("❌ Ambas rutas son requeridas")
        return
    
    print(f"\n{'-' * 60}")
    print(f"CV Software: {cv_software}")
    print(f"CV Data: {cv_data}")
    print(f"{'-' * 60}")
    
    confirm = input("\n¿Los datos son correctos? (s/n): ").lower()
    if confirm != 's':
        return
    
    credentials = manager.load_credentials() or {}
    credentials['cvs'] = {
        "cv_software_path": cv_software,
        "cv_data_path": cv_data
    }
    
    if manager.save_credentials(credentials):
        print("\n✅ Rutas de CVs guardadas exitosamente")
        _update_env_file('CV_SOFTWARE_PATH', cv_software)
        _update_env_file('CV_ENGINEER_PATH', cv_data)


def setup_google_sheets():
    """Configurar Google Sheets para sincronización"""
    print("\n" + "=" * 60)
    print("📊 CONFIGURACIÓN DE GOOGLE SHEETS")
    print("=" * 60)
    
    manager = CredentialsManager()
    
    print("\n📝 Google Sheets ID para sincronizar resultados")
    print("(Lo encuentras en la URL: /spreadsheets/d/[ID])")
    
    sheets_id = input("\nGoogle Sheets ID: ").strip()
    
    if not sheets_id:
        print("❌ ID no puede estar vacío")
        return
    
    confirm = input("\n¿Estás seguro? (s/n): ").lower()
    if confirm != 's':
        return
    
    credentials = manager.load_credentials() or {}
    credentials['google_sheets'] = {"id": sheets_id}
    
    if manager.save_credentials(credentials):
        print("\n✅ Google Sheets ID guardado exitosamente")
        _update_env_file('GOOGLE_SHEETS_ID', sheets_id)


def setup_telegram():
    """Configurar Telegram para notificaciones"""
    print("\n" + "=" * 60)
    print("📱 CONFIGURACIÓN DE TELEGRAM (NOTIFICACIONES)")
    print("=" * 60)
    
    manager = CredentialsManager()
    
    print("\n📝 Configura Telegram para recibir notificaciones")
    print("Crea un bot en: https://t.me/BotFather")
    
    bot_token = getpass("\nBot Token (123:ABC...): ").strip()
    chat_id = input("Tu Chat ID (números): ").strip()
    
    if not bot_token or not chat_id:
        print("❌ Token y Chat ID son requeridos")
        return
    
    print(f"\n{'-' * 60}")
    print(f"Bot Token: {bot_token[:20]}...")
    print(f"Chat ID: {chat_id}")
    print(f"{'-' * 60}")
    
    confirm = input("\n¿Los datos son correctos? (s/n): ").lower()
    if confirm != 's':
        return
    
    credentials = manager.load_credentials() or {}
    credentials['telegram'] = {
        "token": bot_token,
        "chat_id": chat_id
    }
    
    if manager.save_credentials(credentials):
        print("\n✅ Telegram configurado exitosamente")
        _update_env_file('TELEGRAM_TOKEN', bot_token)
        _update_env_file('TELEGRAM_CHAT_ID', chat_id)


def _update_env_file(key: str, value: str):
    """Actualiza o agrega variable al archivo .env"""
    try:
        env_file = Path(".env")
        
        if not env_file.exists():
            with open(env_file, 'w') as f:
                f.write(f"{key}={value}\n")
            return
        
        # Leer líneas existentes
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        # Actualizar o agregar
        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                updated = True
                break
        
        if not updated:
            lines.append(f"{key}={value}\n")
        
        # Escribir
        with open(env_file, 'w') as f:
            f.writelines(lines)
            
    except Exception as e:
        print(f"⚠️  No se pudo actualizar .env: {e}")


def test_credentials():
    """Prueba que las credenciales se puedan leer correctamente"""
    print("\n🧪 Probando lectura de credenciales...")
    
    manager = CredentialsManager()
    credentials = manager.load_credentials()
    
    if credentials and 'linkedin' in credentials:
        print("\n✅ Credenciales de LinkedIn encontradas:")
        print(f"   Email: {credentials['linkedin']['username']}")
        print(f"   Password: {'*' * len(credentials['linkedin']['password'])}")
    else:
        print("\n❌ No se encontraron credenciales de LinkedIn")
    
    if credentials and 'openrouter' in credentials:
        api_key = credentials['openrouter']['api_key']
        print("\n✅ OpenRouter API key encontrada:")
        print(f"   Key: {api_key[:20]}...{api_key[-10:]}")
    else:
        print("\n⚠️  OpenRouter no configurado")
    
    if credentials and 'cvs' in credentials:
        print("\n✅ CVs configurados:")
        print(f"   Software: {credentials['cvs'].get('cv_software_path', 'N/A')}")
        print(f"   Data: {credentials['cvs'].get('cv_data_path', 'N/A')}")
    else:
        print("\n⚠️  CVs no configurados")
    
    if credentials and 'google_sheets' in credentials:
        print("\n✅ Google Sheets configurado:")
        print(f"   ID: {credentials['google_sheets']['id'][:30]}...")
    else:
        print("\n⚠️  Google Sheets no configurado")
    
    if credentials and 'telegram' in credentials:
        print("\n✅ Telegram configurado:")
        print(f"   Bot Token: {credentials['telegram']['token'][:20]}...")
    else:
        print("\n⚠️  Telegram no configurado")
    
    return bool(credentials and 'linkedin' in credentials)


def main():
    """Función principal con menú interactivo"""
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "setup":
            setup_linkedin_credentials()
        elif command == "setup-openrouter":
            setup_openrouter_credentials()
        elif command == "setup-cvs":
            setup_cv_paths()
        elif command == "setup-sheets":
            setup_google_sheets()
        elif command == "setup-telegram":
            setup_telegram()
        elif command == "setup-all":
            setup_linkedin_credentials()
            setup_openrouter_credentials()
            setup_cv_paths()
            setup_google_sheets()
            setup_telegram()
        elif command == "test":
            test_credentials()
        elif command == "delete":
            manager = CredentialsManager()
            confirm = input("⚠️  ¿Estás seguro de eliminar TODAS las credenciales? (s/n): ")
            if confirm.lower() == 's':
                manager.delete_credentials()
        else:
            print(f"Comando desconocido: {command}")
            print("\nUso: python credentials_manager.py [comando]")
            print("\nComandos disponibles:")
            print("  setup            - Configurar LinkedIn")
            print("  setup-openrouter - Configurar OpenRouter IA")
            print("  setup-cvs        - Configurar CVs")
            print("  setup-sheets     - Configurar Google Sheets")
            print("  setup-telegram   - Configurar Telegram")
            print("  setup-all        - Configurar todo")
            print("  test             - Probar credenciales")
            print("  delete           - Eliminar todas las credenciales")
        
        return
    
    # Menú interactivo
    while True:
        print("\n" + "=" * 60)
        print("🔐 GESTOR DE CREDENCIALES - LinkedIn Job Automator")
        print("=" * 60)
        print("\n📌 LINKEDIN (Requerido):")
        print("  1. Configurar credenciales de LinkedIn")
        print("\n🤖 IA & SERVICIOS:")
        print("  2. Configurar OpenRouter (Llama-3.3-70B)")
        print("  3. Configurar CVs (Sistema Dual)")
        print("  4. Configurar Google Sheets (Sincronización)")
        print("  5. Configurar Telegram (Notificaciones)")
        print("\n🔍 MANTENIMIENTO:")
        print("  6. Probar todas las credenciales")
        print("  7. Ver todas las credenciales guardadas")
        print("  8. Eliminar todas las credenciales")
        print("  9. Salir")
        
        choice = input("\nSelecciona una opción (1-9): ").strip()
        
        if choice == "1":
            setup_linkedin_credentials()
        
        elif choice == "2":
            setup_openrouter_credentials()
        
        elif choice == "3":
            setup_cv_paths()
        
        elif choice == "4":
            setup_google_sheets()
        
        elif choice == "5":
            setup_telegram()
        
        elif choice == "6":
            test_credentials()
        
        elif choice == "7":
            manager = CredentialsManager()
            credentials = manager.load_credentials()
            if credentials:
                print("\n📋 Credenciales guardadas:")
                for service, data in credentials.items():
                    print(f"\n🔹 {service.upper()}:")
                    if isinstance(data, dict):
                        for key, value in data.items():
                            if isinstance(value, str) and len(value) > 20:
                                value = f"{value[:20]}...{value[-10:]}"
                            elif isinstance(value, str) and 'password' in key.lower():
                                value = f"{'*' * len(value)}"
                            print(f"   {key}: {value}")
            else:
                print("\n⚠️  No hay credenciales guardadas")
        
        elif choice == "8":
            manager = CredentialsManager()
            confirm = input("\n⚠️  ¿Estás seguro? Esto eliminará TODAS las credenciales (s/n): ")
            if confirm.lower() == 's':
                manager.delete_credentials()
        
        elif choice == "9":
            print("\n👋 ¡Hasta luego!")
            break
        
        else:
            print("\n❌ Opción inválida")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Operación cancelada por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
        sys.exit(1)