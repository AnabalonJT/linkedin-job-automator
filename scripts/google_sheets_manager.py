#!/usr/bin/env python3
"""
Google Sheets Manager
Maneja la integración con Google Sheets para trackear aplicaciones
"""

import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import time


class GoogleSheetsManager:
    """Gestor de Google Sheets para tracking de aplicaciones"""
    
    def __init__(self, credentials_path: str, spreadsheet_id: str):
        """
        Inicializa el gestor
        
        Args:
            credentials_path: Ruta al archivo de credenciales JSON
            spreadsheet_id: ID del Google Sheet
        """
        self.credentials_path = Path(credentials_path)
        self.spreadsheet_id = spreadsheet_id
        
        # Scopes necesarios
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        self.client = None
        self.spreadsheet = None
        
        self._authenticate()
    
    def _authenticate(self):
        """Autentica con Google Sheets"""
        try:
            creds = Credentials.from_service_account_file(
                str(self.credentials_path),
                scopes=self.scopes
            )
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            print("✓ Autenticado con Google Sheets")
        except Exception as e:
            print(f"✗ Error autenticando: {str(e)}")
            raise
    
    def get_or_create_worksheet(self, title: str, headers: List[str] = None) -> gspread.Worksheet:
        """
        Obtiene o crea una hoja de trabajo
        
        Args:
            title: Nombre de la hoja
            headers: Encabezados si es una hoja nueva
        
        Returns:
            Worksheet de gspread
        """
        try:
            # Intentar obtener hoja existente
            worksheet = self.spreadsheet.worksheet(title)
            print(f"✓ Hoja '{title}' encontrada")
            return worksheet
        except gspread.WorksheetNotFound:
            # Crear nueva hoja, pero manejar posible condición de carrera
            try:
                worksheet = self.spreadsheet.add_worksheet(
                    title=title,
                    rows=1000,
                    cols=20
                )

                # Agregar encabezados si se proporcionan
                if headers:
                    worksheet.append_row(headers)
                    # Formatear encabezados
                    worksheet.format('A1:Z1', {
                        "textFormat": {"bold": True},
                        "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
                    })

                print(f"✓ Hoja '{title}' creada")
                return worksheet

            except Exception as e:
                # Si al crear la hoja la API indica que ya existe (condición de carrera), intentar recuperarla
                err_msg = str(e)
                if 'already exists' in err_msg or 'A sheet with the name' in err_msg:
                    try:
                        worksheet = self.spreadsheet.worksheet(title)
                        print(f"✓ Hoja '{title}' encontrada después de intento de creación")
                        return worksheet
                    except Exception:
                        # Re-raise original exception si no se puede recuperar
                        raise
                # Re-raise para cualquier otro error
                raise
    
    def add_job_application(self, job: Dict[str, Any], result: Dict[str, Any] = None):
        """
        Agrega una aplicación a la hoja de Postulaciones
        
        Args:
            job: Datos del trabajo
            result: Resultado de la aplicación (opcional)
        """
        worksheet = self.get_or_create_worksheet(
            'Postulaciones',
            headers=[
                'ID', 'Fecha Aplicación', 'Empresa', 'Puesto', 'URL',
                'Ubicación', 'Tipo Aplicación', 'CV Usado', 'Estado',
                'Último Update', 'Notas', 'Preguntas Pendientes'
            ]
        )
        
        # Obtener siguiente ID
        all_values = worksheet.get_all_values()
        next_id = len(all_values)  # Incluye header
        
        # Preparar datos
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        status = 'PENDIENTE'
        cv_used = 'N/A'
        notes = ''
        
        if result:
            status = result.get('status', 'PENDIENTE')
            cv_used = result.get('cv_used', 'N/A') or 'N/A'
            
            if result.get('error'):
                notes = result['error']
            
            if result.get('questions_encountered'):
                num_questions = len(result['questions_encountered'])
                notes += f" | {num_questions} preguntas sin respuesta"
        
        row = [
            next_id,
            now,
            job.get('company', 'N/A'),
            job.get('title', 'N/A'),
            job.get('url', 'N/A'),
            job.get('location', 'N/A'),
            job.get('application_type', 'AUTO'),
            cv_used,
            status,
            now,
            notes,
            'No' if not result or not result.get('questions_encountered') else 'Sí'
        ]
        
        worksheet.append_row(row)
        print(f"  ✓ Agregado a Google Sheets: {job.get('title')} - {status}")
    
    def update_job_status(self, job_url: str, status: str, notes: str = ""):
        """
        Actualiza el estado de un trabajo existente
        
        Args:
            job_url: URL del trabajo
            status: Nuevo estado
            notes: Notas adicionales
        """
        worksheet = self.spreadsheet.worksheet('Postulaciones')
        
        # Buscar la fila con esta URL
        try:
            cell = worksheet.find(job_url)
            row_number = cell.row
            
            # Actualizar estado (columna I = 9)
            worksheet.update_cell(row_number, 9, status)
            
            # Actualizar timestamp (columna J = 10)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            worksheet.update_cell(row_number, 10, now)
            
            # Agregar notas si se proporcionan (columna K = 11)
            if notes:
                current_notes = worksheet.cell(row_number, 11).value or ""
                updated_notes = f"{current_notes} | {notes}" if current_notes else notes
                worksheet.update_cell(row_number, 11, updated_notes)
            
            print(f"  ✓ Actualizado en Google Sheets: {status}")
            
        except gspread.CellNotFound:
            print(f"  ✗ Trabajo no encontrado en Google Sheets")
    
    def add_pending_question(self, question: str, job_url: str):
        """
        Agrega una pregunta pendiente a la hoja de Preguntas_Pendientes
        
        Args:
            question: Texto de la pregunta
            job_url: URL del trabajo relacionado
        """
        try:
            worksheet = self.get_or_create_worksheet(
                'Preguntas_Pendientes',
                headers=['Fecha', 'Pregunta', 'URL Oferta', 'Estado']
            )
            
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Verificar si la pregunta ya existe
            all_values = worksheet.get_all_values()
            for row in all_values[1:]:  # Skip header
                if len(row) > 1 and row[1] == question:  # Pregunta ya existe
                    return
            
            row = [
                now,
                question,
                job_url,
                'PENDIENTE'
            ]
            
            worksheet.append_row(row)
            print(f"  ✓ Pregunta agregada a Google Sheets")
        except Exception as e:
            print(f"  ✗ Error agregando pregunta: {str(e)}")
            # No fallar si las preguntas no se pueden agregar
            pass
    
    def update_dashboard(self):
        """Verifica/crea el dashboard pero NO lo actualiza (las fórmulas se actualizan solas)"""
        try:
            # Solo asegurarse que existe la hoja Dashboard
            # Las fórmulas en Google Sheets se actualizan automáticamente
            dashboard_ws = self.get_or_create_worksheet(
                'Dashboard',
                headers=['Métrica', 'Valor']
            )
            
            # NO actualizar/limpiar - dejar que las fórmulas hagan su trabajo
            # El Dashboard debe tener fórmulas como:
            # - Total Postulaciones: =COUNTA(Postulaciones!A:A)-1
            # - Aplicadas esta semana: =COUNTIFS(Postulaciones!B:B,">="&TODAY()-7)
            # - En Revisión: =COUNTIF(Postulaciones!I:I,"EN_REVISION")
            # - Entrevistas: =COUNTIF(Postulaciones!I:I,"ENTREVISTA")
            # - Rechazadas: =COUNTIF(Postulaciones!I:I,"RECHAZADO")
            # - Tasa de Respuesta: =IF(B2>0,B4/B2*100,0)&"%"
            
            print(f"  ✓ Dashboard verificado (las fórmulas se actualizan automáticamente)")
        except Exception as e:
            print(f"  ✗ Error verificando dashboard: {str(e)}")
            # No fallar si el dashboard no se puede verificar
            pass
    
    def get_all_applied_urls(self) -> set:
        """
        Obtiene todas las URLs de trabajos ya aplicados
        
        Returns:
            Set de URLs
        """
        try:
            worksheet = self.spreadsheet.worksheet('Postulaciones')
            all_data = worksheet.get_all_values()[1:]  # Skip header
            
            # Columna E (índice 4) tiene las URLs
            urls = {row[4] for row in all_data if len(row) > 4 and row[4]}
            
            return urls
        except gspread.WorksheetNotFound:
            return set()
    
    def get_all_jobs_from_sheets(self) -> list:
        """
        Obtiene todos los trabajos ya registrados en Postulaciones
        
        Returns:
            Lista de diccionarios con los trabajos
        """
        try:
            worksheet = self.spreadsheet.worksheet('Postulaciones')
            all_data = worksheet.get_all_values()[1:]  # Skip header
            
            jobs = []
            for row in all_data:
                if len(row) > 4:  # Asegurar que hay suficientes columnas
                    job = {
                        'title': row[3] if len(row) > 3 else 'N/A',
                        'company': row[2] if len(row) > 2 else 'N/A',
                        'url': row[4] if len(row) > 4 else 'N/A',
                        'location': row[5] if len(row) > 5 else 'N/A',
                        'posted_date': 'N/A',
                        'source': 'google_sheets'
                    }
                    jobs.append(job)
            
            return jobs
        except gspread.WorksheetNotFound:
            return []


def main():
    """Función de prueba"""
    import json
    from utils import Config
    
    print("📊 Google Sheets Manager - Prueba")
    print("=" * 60)
    
    config = Config()
    
    # Obtener configuración
    sheets_id = config.get_env_var('GOOGLE_SHEETS_ID')
    creds_path = Path('config/google_credentials.json')
    
    if not sheets_id:
        print("✗ GOOGLE_SHEETS_ID no configurado en .env")
        return
    
    if not creds_path.exists():
        print(f"✗ Archivo de credenciales no encontrado: {creds_path}")
        return
    
    # Crear manager
    manager = GoogleSheetsManager(str(creds_path), sheets_id)
    
    # Cargar resultados de aplicaciones
    results_file = Path('data/logs/application_results.json')
    if not results_file.exists():
        print("✗ No hay resultados de aplicaciones para subir")
        return
    
    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Cargar trabajos
    jobs_file = Path('data/logs/jobs_found.json')
    with open(jobs_file, 'r', encoding='utf-8') as f:
        jobs = json.load(f)
    
    # Crear diccionario de resultados por URL
    results_by_url = {r['job_url']: r for r in results}
    
    print(f"\n📤 Subiendo {len(results)} resultados a Google Sheets...")
    
    # Subir cada resultado
    for job in jobs:
        if job['url'] in results_by_url:
            result = results_by_url[job['url']]
            manager.add_job_application(job, result)
            
            # Agregar preguntas pendientes
            if result.get('questions_encountered'):
                for question in result['questions_encountered']:
                    manager.add_pending_question(question, job['url'])
            
            time.sleep(1)  # Rate limiting
    
    # Actualizar dashboard
    print("\n📊 Actualizando dashboard...")
    manager.update_dashboard()
    
    print("\n✅ Proceso completado")
    print(f"🔗 Ver en: https://docs.google.com/spreadsheets/d/{sheets_id}")


if __name__ == "__main__":
    main()