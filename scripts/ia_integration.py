#!/usr/bin/env python3
"""
IA Integration Module
Integración de sistemas IA en el flujo de postulación de LinkedIn
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from utils import Logger

# Importar módulos IA
try:
    from openrouter_client import OpenRouterClient
    from cv_processor import CVProcessor
    from ia_classifier import AIClassifier
    IA_AVAILABLE = True
except ImportError as e:
    IA_AVAILABLE = False


class IAIntegration:
    """
    Integración de todos los componentes IA para el flujo de postulación
    """
    
    def __init__(self, logger: Logger, debug: bool = False):
        """
        Inicializa la integración de IA
        
        Args:
            logger: Logger para registro
            debug: Habilitar modo debug
        """
        self.logger = logger
        self.debug = debug or os.getenv('DEBUG', 'False').lower() == 'true'
        self.enabled = IA_AVAILABLE and os.getenv('OPENROUTER_API_KEY')
        
        if not self.enabled:
            if not IA_AVAILABLE:
                self.logger.warning("⚠ Módulos IA no disponibles. Usando modo compatibilidad.")
            else:
                self.logger.warning("⚠ OPENROUTER_API_KEY no configurada. IA deshabilitada.")
            return
        
        try:
            # Inicializar componentes IA
            self.logger.info("🤖 Inicializando módulos IA...")
            
            # 1. CVProcessor - cargar CV unificado
            cv_processor = CVProcessor(
                cv_software_path=os.getenv('CV_SOFTWARE_PATH', 'config/CV Software Engineer Anabalon.pdf'),
                cv_engineer_path=os.getenv('CV_ENGINEER_PATH', 'config/CV Automatización_Data Anabalón.pdf')
            )
            
            # Cargar CV unificado
            cv_context = cv_processor.load_or_create()
            
            # Convertir a formato string para AIClassifier
            cv_context_str = cv_processor.get_context_as_string(cv_context)
            
            self.logger.info(f"  ✓ CV unificado cargado ({len(cv_context_str)} chars)")
            
            # 2. AIClassifier - inicializar clasificador
            confidence_threshold = float(os.getenv('IA_CONFIDENCE_THRESHOLD', '0.85'))
            self.classifier = AIClassifier(
                cv_contexts={'unified': cv_context_str},
                confidence_threshold=confidence_threshold
            )
            self.logger.info(f"  ✓ Clasificador inicializado (threshold: {confidence_threshold})")
            
            # Guardar referencia al procesador para acceso posterior
            self.cv_processor = cv_processor
            
            self.logger.success("✓ Módulos IA inicializados correctamente")
            
        except Exception as e:
            self.logger.error(f"❌ Error inicializando IA: {str(e)}")
            self.enabled = False
    
    def classify_job(self, job_title: str, job_description: str, job_requirements: str = "") -> Dict[str, Any]:
        """
        Clasifica un trabajo y recomienda CV
        
        Args:
            job_title: Título del trabajo
            job_description: Descripción del trabajo
            job_requirements: Requisitos del trabajo
        
        Returns:
            Diccionario con clasificación y recomendación CV
        """
        if not self.enabled:
            return {
                'job_type': 'unknown',
                'match_percentage': 0,
                'confidence': 0,
                'recommended_cv': 'software',  # Por defecto
                'reasoning': 'IA no disponible',
                'auto_submit': False
            }
        
        try:
            if self.debug:
                self.logger.info(f"🔍 Clasificando: {job_title[:50]}...")
            
            result = self.classifier.classify_job(
                job_title=job_title,
                job_description=job_description,
                job_requirements=job_requirements
            )
            
            cv_type = result.get('recommended_cv', 'software')
            confidence = result.get('confidence', 0)
            
            # Aplicar el CV recomendado
            self.set_cv_type(cv_type)
            
            if self.debug:
                self.logger.info(f"  → CV recomendado: {cv_type} (confianza: {confidence:.2f})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error clasificando trabajo: {str(e)}")
            return {
                'job_type': 'unknown',
                'match_percentage': 0,
                'confidence': 0,
                'recommended_cv': 'software',
                'reasoning': f'Error: {str(e)}',
                'auto_submit': False
            }
    
    def set_cv_type(self, cv_type: str) -> bool:
        """
        Define el tipo de CV a usar para responder preguntas
        
        Args:
            cv_type: 'software' o 'engineer'
        
        Returns:
            True si fue exitoso
        """
        if not self.enabled:
            return False
        
        try:
            self.classifier.set_cv_type(cv_type)
            if self.debug:
                self.logger.info(f"📄 CV activo: {cv_type}")
            return True
        except Exception as e:
            self.logger.warning(f"Error configurando CV: {str(e)}")
            return False
    
    def answer_question(
        self,
        question_text: str,
        question_type: str = "text",
        options: list = None,
        previous_answers: dict = None
    ) -> Dict[str, Any]:
        """
        Obtiene respuesta IA para una pregunta
        
        Args:
            question_text: Texto de la pregunta
            question_type: Tipo (text, textarea, choice, dropdown, date, rating)
            options: Opciones disponibles
            previous_answers: Respuestas anteriores para contexto
        
        Returns:
            Diccionario con respuesta y metadata
        """
        if not self.enabled:
            return {
                'answer': '',
                'confidence': 0,
                'reasoning': 'IA no disponible',
                'sources': [],
                'auto_submit': False,
                'marked_as_manual': True
            }
        
        try:
            if self.debug:
                self.logger.info(f"❓ Respondiendo: {question_text[:50]}... ({question_type})")
            
            result = self.classifier.answer_question(
                question_text=question_text,
                question_type=question_type,
                options=options or [],
                previous_answers=previous_answers or {}
            )
            
            confidence = result.get('confidence', 0)
            answer = result.get('answer', '')
            auto_submit = result.get('auto_submit', False)
            
            if self.debug:
                status = "✅ AUTO" if auto_submit else "⚠️ MANUAL"
                self.logger.info(f"  → {status} [conf: {confidence:.2f}] '{answer[:40]}'")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error respondiendo pregunta: {str(e)}")
            return {
                'answer': '',
                'confidence': 0,
                'reasoning': f'Error: {str(e)}',
                'sources': [],
                'auto_submit': False,
                'marked_as_manual': True
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de IA
        
        Returns:
            Diccionario con stats
        """
        if not self.enabled or not hasattr(self, 'classifier'):
            return {
                'enabled': False,
                'total_jobs_classified': 0,
                'total_questions_answered': 0,
                'automation_rate': 0,
                'average_confidence': 0
            }
        
        stats = self.classifier.get_stats()
        
        return {
            'enabled': True,
            'total_jobs_classified': stats.get('total_classifications', 0),
            'total_questions_answered': stats.get('total_questions', 0),
            'auto_answered': stats.get('auto_answered', 0),
            'manual_marked': stats.get('manual_questions', 0),
            'cv_type_usage': stats.get('cv_type_usage', {}),
            'average_confidence': stats.get('average_confidence', 0),
            'automation_rate': stats.get('automation_rate', 0)
        }
    
    def format_stats_for_telegram(self) -> str:
        """
        Formatea stats para enviar en Telegram
        
        Returns:
            String formateado
        """
        stats = self.get_stats()
        
        if not stats['enabled']:
            return "🤖 IA: Deshabilitada"
        
        message = "🤖 IA Stats:\n"
        message += f"• Clasificaciones: {stats['total_jobs_classified']}\n"
        message += f"• Preguntas respondidas: {stats['total_questions_answered']}\n"
        message += f"• Automatizadas: {stats['auto_answered']} ({stats['automation_rate']:.1f}%)\n"
        message += f"• Manuales: {stats['manual_marked']}\n"
        message += f"• Confianza promedio: {stats['average_confidence']:.2f}/1.0\n"
        
        if stats['cv_type_usage']:
            message += "• CVs usados: "
            usage = stats['cv_type_usage']
            parts = []
            for cv_type, count in usage.items():
                parts.append(f"{cv_type}({count})")
            message += ", ".join(parts)
        
        return message
    
    def close(self):
        """Limpia recursos"""
        if hasattr(self, 'extractor'):
            try:
                # El extractor usa Selenium, que requiere limpieza
                pass
            except:
                pass


# Ejemplo de uso
if __name__ == "__main__":
    logger = Logger()
    ia = IAIntegration(logger, debug=True)
    
    if ia.enabled:
        # Clasificar trabajo
        classification = ia.classify_job(
            job_title="Senior Python Developer",
            job_description="Buscamos un desarrollador Python con 5+ años de experiencia...",
            job_requirements="Python, Django, PostgreSQL, Docker"
        )
        logger.info(f"Clasificación: {json.dumps(classification, indent=2)}")
        
        # Cambiar a CV recomendado
        ia.set_cv_type(classification['recommended_cv'])
        
        # Responder pregunta
        answer = ia.answer_question(
            question_text="¿Cuál es tu experiencia con Python?",
            question_type="textarea",
            options=[]
        )
        logger.info(f"Respuesta: {json.dumps(answer, indent=2)}")
        
        # Mostrar stats
        stats = ia.get_stats()
        logger.info(f"Stats: {json.dumps(stats, indent=2)}")
    else:
        logger.warning("IA no disponible")
