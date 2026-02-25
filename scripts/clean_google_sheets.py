#!/usr/bin/env python3
"""
Script para limpiar duplicados en Google Sheets.

Elimina filas duplicadas basándose en la URL del trabajo, manteniendo solo
la primera ocurrencia de cada trabajo.
"""

import sys
from pathlib import Path
from google_sheets_manager import GoogleSheetsManager
from utils import Config, Logger

def clean_duplicates():
    """Limpia trabajos duplicados del Google Sheet"""
    
    # Inicializar config y logger
    config = Config()
    logger = Logger()
    
    logger.info("🧹 Limpiando duplicados en Google Sheets...")
    
    try:
        # Inicializar Google Sheets Manager
        sheets_id = config.get_env_var('GOOGLE_SHEETS_ID')
        credentials_path = 'config/google_credentials.json'
        
        if not sheets_id:
            logger.error("❌ GOOGLE_SHEETS_ID no configurado en .env")
            return False
        
        if not Path(credentials_path).exists():
            logger.error(f"❌ Archivo de credenciales no encontrado: {credentials_path}")
            return False
        
        manager = GoogleSheetsManager(credentials_path, sheets_id)
        logger.info("✓ Conectado a Google Sheets")
        
        # Obtener la hoja de Postulaciones usando el método correcto
        worksheet = manager.get_or_create_worksheet(
            'Postulaciones',
            headers=[
                'ID', 'Fecha Aplicación', 'Empresa', 'Puesto', 'URL',
                'Ubicación', 'Tipo Aplicación', 'CV Usado', 'Estado',
                'Último Update', 'Notas', 'Preguntas Pendientes'
            ]
        )
        
        # Obtener todas las filas
        sheet = worksheet.get_all_records()
        logger.info(f"📊 Total de filas: {len(sheet)}")
        
        # Identificar duplicados por URL
        seen_urls = set()
        rows_to_delete = []
        
        for idx, row in enumerate(sheet, start=2):  # Start at 2 (row 1 is header)
            url = row.get('URL', '').strip()
            if not url:
                continue
            
            if url in seen_urls:
                rows_to_delete.append(idx)
                logger.info(f"  🔍 Duplicado encontrado: {row.get('Título', 'Sin título')} (fila {idx})")
            else:
                seen_urls.add(url)
        
        if not rows_to_delete:
            logger.info("✅ No se encontraron duplicados")
            return True
        
        logger.info(f"🗑️  Eliminando {len(rows_to_delete)} filas duplicadas...")
        
        # Eliminar filas en orden inverso (de abajo hacia arriba)
        # para que los índices no cambien
        # Agregar delay para evitar rate limit (60 escrituras por minuto = 1 por segundo)
        for idx, row_idx in enumerate(reversed(rows_to_delete), 1):
            try:
                worksheet.delete_rows(row_idx)
                logger.info(f"  ✓ Fila {row_idx} eliminada ({idx}/{len(rows_to_delete)})")
                
                # Delay de 1.5 segundos entre eliminaciones para evitar rate limit
                if idx < len(rows_to_delete):  # No esperar después de la última
                    import time
                    time.sleep(1.5)
                    
            except Exception as e:
                logger.warning(f"  ⚠️  Error eliminando fila {row_idx}: {e}")
                # Si es rate limit, esperar más tiempo
                if '429' in str(e) or 'RATE_LIMIT' in str(e):
                    logger.warning("  ⏸️  Rate limit alcanzado, esperando 60 segundos...")
                    import time
                    time.sleep(60)
                    # Reintentar
                    try:
                        worksheet.delete_rows(row_idx)
                        logger.info(f"  ✓ Fila {row_idx} eliminada (reintento exitoso)")
                    except Exception as e2:
                        logger.error(f"  ✗ Fallo reintento para fila {row_idx}: {e2}")
        
        logger.success(f"✅ Limpieza completada. {len(rows_to_delete)} duplicados eliminados")
        logger.info(f"📊 Filas restantes: {len(sheet) - len(rows_to_delete)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error limpiando duplicados: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = clean_duplicates()
    sys.exit(0 if success else 1)
