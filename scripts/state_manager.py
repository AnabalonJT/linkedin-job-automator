"""
Gestor de estado para persistencia y recuperación.

Este módulo maneja el estado de trabajos procesados para evitar duplicados
y permitir recuperación después de interrupciones.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from models import ProcessedJob

logger = logging.getLogger(__name__)


class StateManager:
    """
    Maneja el estado de postulaciones para recuperación.
    
    Mantiene un archivo JSON con el estado de todos los trabajos procesados,
    permitiendo:
    - Evitar duplicar postulaciones
    - Reanudar desde donde se quedó si el proceso se interrumpe
    - Limpiar entradas antiguas automáticamente
    """
    
    STATE_FILE = 'data/logs/application_state.json'
    
    def __init__(self, state_file: str = None):
        """
        Inicializa el gestor de estado.
        
        Args:
            state_file: Ruta al archivo de estado (opcional, usa default si no se provee)
        """
        self.state_file = state_file or self.STATE_FILE
        self._ensure_state_file_exists()
        logger.info(f"StateManager inicializado: {self.state_file}")
    
    def _ensure_state_file_exists(self):
        """Asegura que el archivo de estado y su directorio existan."""
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        
        # Crear archivo vacío si no existe
        if not os.path.exists(self.state_file):
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            logger.info(f"Archivo de estado creado: {self.state_file}")
    
    def load_state(self) -> Dict[str, ProcessedJob]:
        """
        Carga el estado previo desde archivo.
        
        Returns:
            Dict con URL como key y ProcessedJob como value
        """
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convertir dict a ProcessedJob objects
            state = {}
            for url, job_data in data.items():
                try:
                    # Parsear timestamp
                    timestamp = datetime.fromisoformat(job_data['timestamp'])
                    
                    state[url] = ProcessedJob(
                        url=job_data['url'],
                        status=job_data['status'],
                        timestamp=timestamp,
                        cv_used=job_data.get('cv_used'),
                        error_message=job_data.get('error_message')
                    )
                except Exception as e:
                    logger.warning(f"Error al parsear job {url}: {e}")
                    continue
            
            logger.info(f"Estado cargado: {len(state)} trabajos")
            return state
            
        except FileNotFoundError:
            logger.warning(f"Archivo de estado no encontrado: {self.state_file}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear JSON del estado: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error al cargar estado: {e}")
            return {}
    
    def save_job_state(
        self,
        job_url: str,
        status: str,
        timestamp: datetime = None,
        cv_used: str = None,
        error_message: str = None
    ):
        """
        Guarda el estado de un trabajo procesado.
        
        Args:
            job_url: URL del trabajo
            status: Estado (APPLIED, MANUAL, NO_DISPONIBLE, ERROR, INSEGURO)
            timestamp: Fecha y hora del procesamiento (default: ahora)
            cv_used: CV utilizado (opcional)
            error_message: Mensaje de error si falló (opcional)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            # Cargar estado actual
            state = self.load_state()
            
            # Agregar/actualizar trabajo
            state[job_url] = ProcessedJob(
                url=job_url,
                status=status,
                timestamp=timestamp,
                cv_used=cv_used,
                error_message=error_message
            )
            
            # Convertir a dict para JSON
            state_dict = {}
            for url, job in state.items():
                state_dict[url] = {
                    'url': job.url,
                    'status': job.status,
                    'timestamp': job.timestamp.isoformat(),
                    'cv_used': job.cv_used,
                    'error_message': job.error_message
                }
            
            # Guardar
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Estado guardado: {job_url} → {status}")
            
        except Exception as e:
            logger.error(f"Error al guardar estado: {e}")
    
    def is_job_processed(self, job_url: str) -> bool:
        """
        Verifica si un trabajo ya fue procesado.
        
        Args:
            job_url: URL del trabajo
            
        Returns:
            True si el trabajo ya fue procesado, False en caso contrario
        """
        state = self.load_state()
        return job_url in state
    
    def get_job_status(self, job_url: str) -> Optional[ProcessedJob]:
        """
        Obtiene el estado de un trabajo específico.
        
        Args:
            job_url: URL del trabajo
            
        Returns:
            ProcessedJob si existe, None si no
        """
        state = self.load_state()
        return state.get(job_url)
    
    def cleanup_old_entries(self, days: int = 30):
        """
        Elimina entradas más antiguas que N días.
        
        Args:
            days: Número de días (default: 30)
        """
        try:
            state = self.load_state()
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Filtrar entradas antiguas
            initial_count = len(state)
            state = {
                url: job for url, job in state.items()
                if job.timestamp > cutoff_date
            }
            removed_count = initial_count - len(state)
            
            if removed_count > 0:
                # Guardar estado limpio
                state_dict = {}
                for url, job in state.items():
                    state_dict[url] = {
                        'url': job.url,
                        'status': job.status,
                        'timestamp': job.timestamp.isoformat(),
                        'cv_used': job.cv_used,
                        'error_message': job.error_message
                    }
                
                with open(self.state_file, 'w', encoding='utf-8') as f:
                    json.dump(state_dict, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Limpieza completada: {removed_count} entradas eliminadas (> {days} días)")
            else:
                logger.info(f"No hay entradas antiguas para limpiar (> {days} días)")
                
        except Exception as e:
            logger.error(f"Error al limpiar entradas antiguas: {e}")
    
    def get_statistics(self) -> dict:
        """
        Obtiene estadísticas del estado actual.
        
        Returns:
            Dict con estadísticas (total, por estado, etc.)
        """
        state = self.load_state()
        
        stats = {
            'total': len(state),
            'by_status': {},
            'oldest_entry': None,
            'newest_entry': None
        }
        
        if not state:
            return stats
        
        # Contar por estado
        for job in state.values():
            status = job.status
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
        
        # Encontrar entradas más antigua y más nueva
        timestamps = [job.timestamp for job in state.values()]
        stats['oldest_entry'] = min(timestamps).isoformat()
        stats['newest_entry'] = max(timestamps).isoformat()
        
        return stats
