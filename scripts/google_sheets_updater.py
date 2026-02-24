"""
Actualizador de Google Sheets para tracking de postulaciones.

Este módulo envuelve GoogleSheetsManager y agrega funcionalidad específica
para actualizar el estado de postulaciones con información detallada de IA.
"""

import logging
from typing import List, Optional
from datetime import datetime
from google_sheets_manager import GoogleSheetsManager

logger = logging.getLogger(__name__)


class GoogleSheetsUpdater:
    """
    Actualiza Google Sheets con resultados de postulaciones.
    
    Maneja actualizaciones con información detallada incluyendo:
    - Estado de la postulación (APPLIED, MANUAL, NO_DISPONIBLE, ERROR, INSEGURO)
    - CV utilizado
    - Notas sobre confianza de IA
    - Preguntas con baja confianza
    """
    
    # Estados válidos
    VALID_STATUSES = ['APPLIED', 'MANUAL', 'NO_DISPONIBLE', 'ERROR', 'INSEGURO']
    
    def __init__(self, credentials_path: str, spreadsheet_id: str):
        """
        Inicializa el actualizador.
        
        Args:
            credentials_path: Ruta al archivo de credenciales JSON de Google
            spreadsheet_id: ID del Google Sheet
        """
        try:
            self.manager = GoogleSheetsManager(credentials_path, spreadsheet_id)
            logger.info("GoogleSheetsUpdater inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar GoogleSheetsUpdater: {e}")
            raise
    
    def update_application(
        self,
        job_id: str,
        job_url: str,
        job_title: str,
        company: str,
        location: str,
        status: str,
        cv_used: str = None,
        notes: str = "",
        questions_answered: int = 0,
        average_confidence: float = 0.0
    ):
        """
        Actualiza una fila en Google Sheets con el resultado de la postulación.
        
        Args:
            job_id: ID del trabajo
            job_url: URL del trabajo
            job_title: Título del puesto
            company: Nombre de la empresa
            location: Ubicación del trabajo
            status: Estado (APPLIED, MANUAL, NO_DISPONIBLE, ERROR, INSEGURO)
            cv_used: Nombre del CV utilizado
            notes: Notas adicionales
            questions_answered: Número de preguntas respondidas
            average_confidence: Confianza promedio de las respuestas
        """
        # Validar estado
        if status not in self.VALID_STATUSES:
            logger.warning(f"Estado inválido '{status}', usando 'ERROR'")
            status = 'ERROR'
            notes = f"Estado inválido: {status}. {notes}"
        
        logger.info(f"Actualizando Google Sheets: {job_title} → {status}")
        logger.info(f"  URL: {job_url}")
        logger.info(f"  CV usado: {cv_used}")
        logger.info(f"  Preguntas respondidas: {questions_answered}")
        logger.info(f"  Confianza promedio: {average_confidence:.2f}")
        
        try:
            # Preparar datos del trabajo
            job_data = {
                'title': job_title,
                'company': company,
                'url': job_url,
                'location': location,
                'application_type': 'AUTO'
            }
            
            # Preparar resultado
            result_data = {
                'status': status,
                'cv_used': cv_used,
                'error': notes if status in ['ERROR', 'NO_DISPONIBLE'] else None
            }
            
            # Agregar información de confianza a las notas si es INSEGURO
            if status == 'INSEGURO' and average_confidence > 0:
                confidence_note = f"Confianza promedio: {average_confidence:.2f}"
                notes = f"{confidence_note}. {notes}" if notes else confidence_note
                result_data['error'] = notes
            
            # Usar el manager existente para agregar la aplicación
            self.manager.add_job_application(job_data, result_data)
            
            logger.info(f"✅ Actualización exitosa en Google Sheets")
            
        except Exception as e:
            logger.error(f"❌ Error al actualizar Google Sheets: {e}")
            # No lanzar excepción - continuar con el proceso
    
    def add_confidence_notes(self, job_url: str, low_confidence_questions: List[str]):
        """
        Agrega notas sobre preguntas con baja confianza.
        
        Args:
            job_url: URL del trabajo
            low_confidence_questions: Lista de preguntas con baja confianza
        """
        if not low_confidence_questions:
            return
        
        logger.info(f"Agregando notas de confianza para {len(low_confidence_questions)} preguntas")
        
        try:
            # Construir nota
            questions_text = ", ".join(low_confidence_questions[:3])  # Primeras 3
            if len(low_confidence_questions) > 3:
                questions_text += f" (y {len(low_confidence_questions) - 3} más)"
            
            notes = f"Preguntas con baja confianza: {questions_text}"
            
            # Actualizar estado
            self.manager.update_job_status(job_url, 'INSEGURO', notes)
            
            # Agregar preguntas pendientes a hoja separada
            for question in low_confidence_questions:
                self.manager.add_pending_question(question, job_url)
            
            logger.info(f"✅ Notas de confianza agregadas")
            
        except Exception as e:
            logger.error(f"❌ Error al agregar notas de confianza: {e}")
            # No lanzar excepción - continuar con el proceso
    
    def mark_as_unavailable(self, job_url: str, job_title: str, company: str, reason: str = ""):
        """
        Marca un trabajo como no disponible.
        
        Args:
            job_url: URL del trabajo
            job_title: Título del puesto
            company: Nombre de la empresa
            reason: Razón por la que no está disponible
        """
        logger.info(f"Marcando como NO_DISPONIBLE: {job_title}")
        logger.info(f"  Razón: {reason}")
        
        notes = f"No disponible: {reason}" if reason else "Trabajo cerrado o ya no acepta postulaciones"
        
        self.update_application(
            job_id="",
            job_url=job_url,
            job_title=job_title,
            company=company,
            location="N/A",
            status='NO_DISPONIBLE',
            cv_used=None,
            notes=notes
        )
    
    def mark_as_manual(self, job_url: str, job_title: str, company: str, reason: str = ""):
        """
        Marca un trabajo para revisión manual.
        
        Args:
            job_url: URL del trabajo
            job_title: Título del puesto
            company: Nombre de la empresa
            reason: Razón por la que requiere revisión manual
        """
        logger.info(f"Marcando como MANUAL: {job_title}")
        logger.info(f"  Razón: {reason}")
        
        notes = f"Revisión manual requerida: {reason}" if reason else "Requiere revisión manual"
        
        self.update_application(
            job_id="",
            job_url=job_url,
            job_title=job_title,
            company=company,
            location="N/A",
            status='MANUAL',
            cv_used=None,
            notes=notes
        )
    
    def mark_as_error(self, job_url: str, job_title: str, company: str, error_message: str):
        """
        Marca un trabajo con error.
        
        Args:
            job_url: URL del trabajo
            job_title: Título del puesto
            company: Nombre de la empresa
            error_message: Mensaje de error
        """
        logger.error(f"Marcando como ERROR: {job_title}")
        logger.error(f"  Error: {error_message}")
        
        self.update_application(
            job_id="",
            job_url=job_url,
            job_title=job_title,
            company=company,
            location="N/A",
            status='ERROR',
            cv_used=None,
            notes=f"Error: {error_message}"
        )
    
    def get_applied_urls(self) -> set:
        """
        Obtiene todas las URLs de trabajos ya aplicados.
        
        Returns:
            Set de URLs
        """
        try:
            urls = self.manager.get_all_applied_urls()
            logger.info(f"Obtenidas {len(urls)} URLs de trabajos ya aplicados")
            return urls
        except Exception as e:
            logger.error(f"Error al obtener URLs aplicadas: {e}")
            return set()
