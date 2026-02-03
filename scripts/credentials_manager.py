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


def test_credentials():
    """Prueba que las credenciales se puedan leer correctamente"""
    print("\n🧪 Probando lectura de credenciales...")
    
    manager = CredentialsManager()
    credentials = manager.load_credentials()
    
    if credentials and 'linkedin' in credentials:
        print("\n✅ Credenciales de LinkedIn encontradas:")
        print(f"   Email: {credentials['linkedin']['username']}")
        print(f"   Password: {'*' * len(credentials['linkedin']['password'])}")
        return True
    else:
        print("\n❌ No se encontraron credenciales de LinkedIn")
        return False


def main():
    """Función principal con menú interactivo"""
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "setup":
            setup_linkedin_credentials()
        elif command == "test":
            test_credentials()
        elif command == "delete":
            manager = CredentialsManager()
            confirm = input("⚠️  ¿Estás seguro de eliminar TODAS las credenciales? (s/n): ")
            if confirm.lower() == 's':
                manager.delete_credentials()
        else:
            print(f"Comando desconocido: {command}")
            print("\nUso: python credentials_manager.py [setup|test|delete]")
        
        return
    
    # Menú interactivo
    while True:
        print("\n" + "=" * 60)
        print("🔐 GESTOR DE CREDENCIALES - LinkedIn Job Automator")
        print("=" * 60)
        print("\n1. Configurar credenciales de LinkedIn")
        print("2. Probar lectura de credenciales")
        print("3. Ver credenciales guardadas")
        print("4. Eliminar todas las credenciales")
        print("5. Salir")
        
        choice = input("\nSelecciona una opción (1-5): ").strip()
        
        if choice == "1":
            setup_linkedin_credentials()
        
        elif choice == "2":
            test_credentials()
        
        elif choice == "3":
            manager = CredentialsManager()
            credentials = manager.load_credentials()
            if credentials:
                print("\n📋 Credenciales guardadas:")
                for service, data in credentials.items():
                    print(f"\n🔹 {service.upper()}:")
                    print(f"   Usuario: {data['username']}")
                    print(f"   Password: {'*' * len(data['password'])}")
            else:
                print("\n⚠️  No hay credenciales guardadas")
        
        elif choice == "4":
            manager = CredentialsManager()
            confirm = input("\n⚠️  ¿Estás seguro? Esto eliminará TODAS las credenciales (s/n): ")
            if confirm.lower() == 's':
                manager.delete_credentials()
        
        elif choice == "5":
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