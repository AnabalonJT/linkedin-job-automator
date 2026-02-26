#!/usr/bin/env python3
"""
Script de prueba para verificar la configuración de Telegram
"""

import os
from pathlib import Path

# Cargar .env si existe
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

def test_telegram():
    """Prueba la configuración de Telegram"""
    
    print("🔍 Verificando configuración de Telegram...")
    print("=" * 60)
    
    # Verificar variables de entorno
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN no está configurado")
        return False
    else:
        print(f"✓ TELEGRAM_BOT_TOKEN: {bot_token[:10]}...{bot_token[-5:]}")
    
    if not chat_id:
        print("❌ TELEGRAM_CHAT_ID no está configurado")
        return False
    else:
        print(f"✓ TELEGRAM_CHAT_ID: {chat_id}")
    
    print("\n📤 Intentando enviar mensaje de prueba...")
    
    try:
        from telegram_notifier import TelegramNotifier
        
        notifier = TelegramNotifier(bot_token, chat_id)
        
        message = """
<b>🧪 Mensaje de Prueba</b>

Este es un mensaje de prueba del LinkedIn Job Applier.

Si recibes este mensaje, la configuración de Telegram está funcionando correctamente.

✅ Configuración OK
        """.strip()
        
        response = notifier.send_message(message)
        
        if response.get('ok'):
            print("✅ Mensaje enviado exitosamente!")
            print(f"   Message ID: {response.get('result', {}).get('message_id')}")
            return True
        else:
            print(f"❌ Error en respuesta: {response}")
            return False
            
    except Exception as e:
        print(f"❌ Error enviando mensaje: {e}")
        import traceback
        print(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = test_telegram()
    print("=" * 60)
    if success:
        print("✨ Prueba completada exitosamente")
    else:
        print("⚠️  Prueba fallida - revisa la configuración")
