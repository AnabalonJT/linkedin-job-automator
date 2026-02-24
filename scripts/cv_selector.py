"""
Selector de CV usando IA (OpenRouter).

Este módulo selecciona el CV apropiado para cada trabajo basándose en el título
y descripción del trabajo. Usa IA para detectar el idioma y tipo de trabajo,
y mapea al CV correcto.
"""

import logging
import os
from typing import Dict
from openrouter_client import OpenRouterClient
from models import CVRecommendation

logger = logging.getLogger(__name__)


class CVSelector:
    """
    Selecciona el CV apropiado basándose en el trabajo usando IA.
    
    Analiza el título y descripción del trabajo para determinar:
    1. Idioma requerido (inglés o español)
    2. Tipo de trabajo (software engineer vs automatización/data/IA)
    3. CV apropiado según el mapeo definido
    """
    
    # Mapeo de (tipo, idioma) a archivo de CV
    CV_MAPPING = {
        ('software', 'en'): 'config/CV Software Engineer Anabalon.pdf',
        ('software', 'es'): 'config/CV Software Engineer Anabalon.pdf',  # Mismo CV (bilingüe)
        ('engineer', 'en'): 'config/CV Automatización_Data Anabalón.pdf',
        ('engineer', 'es'): 'config/CV Automatización_Data Anabalón.pdf'  # Mismo CV (bilingüe)
    }
    
    # Contexto resumido de cada CV para la IA
    CV_CONTEXTS = {
        'software': """
        CV: Software Engineer
        - 6+ años experiencia desarrollo backend/fullstack
        - Lenguajes: Python, JavaScript, TypeScript, Java
        - Frameworks: Django, FastAPI, React, Node.js
        - Bases de datos: PostgreSQL, MongoDB, Redis
        - Cloud: AWS, Docker, Kubernetes
        - Enfoque: Desarrollo de aplicaciones web, APIs REST, microservicios
        """,
        'engineer': """
        CV: Automatización, Data & IA Engineer
        - 5+ años experiencia en automatización y data engineering
        - Lenguajes: Python, SQL, JavaScript
        - Automatización: Selenium, n8n, Zapier, RPA
        - Data: Pandas, NumPy, ETL pipelines, data warehousing
        - IA/ML: OpenAI, LangChain, RAG, prompt engineering
        - Integraciones: APIs, webhooks, Google Sheets, Telegram
        - Enfoque: Automatización de procesos, análisis de datos, soluciones con IA
        """
    }
    
    def __init__(self, api_key: str = None):
        """
        Inicializa el selector de CV.
        
        Args:
            api_key: API key de OpenRouter (opcional, puede venir de env)
        """
        self.client = OpenRouterClient(api_key=api_key)
        logger.info("CVSelector inicializado")
    
    def select_cv(self, job_title: str, job_description: str) -> CVRecommendation:
        """
        Selecciona el CV apropiado usando OpenRouter.
        
        Analiza el trabajo y determina qué CV es más apropiado basándose en:
        - Palabras clave del título y descripción
        - Requisitos técnicos mencionados
        - Idioma del trabajo
        
        Args:
            job_title: Título del trabajo
            job_description: Descripción completa del trabajo
            
        Returns:
            CVRecommendation con cv_type, language, cv_path, confidence, reasoning
        """
        logger.info(f"Seleccionando CV para: {job_title}")
        
        try:
            # Detectar idioma primero
            language = self.detect_language(job_title + " " + job_description)
            logger.info(f"Idioma detectado: {language}")
            
            # Preparar prompt para la IA
            system_prompt = """Eres un experto en recursos humanos y análisis de ofertas de trabajo.
Tu tarea es determinar qué tipo de CV es más apropiado para una oferta de trabajo.

TIPOS DE CV DISPONIBLES:
1. "software" - Software Engineer: Desarrollo web, APIs, microservicios, backend/fullstack
2. "engineer" - Automatización/Data/IA: Automatización de procesos, data engineering, IA/ML

REGLAS:
- Analiza el título y descripción del trabajo
- Identifica las habilidades y tecnologías requeridas
- Compara con los perfiles de CV disponibles
- Responde SIEMPRE en JSON válido
- Incluye confidence (0.0 a 1.0) basado en qué tan claro es el match"""
            
            user_message = f"""TRABAJO A ANALIZAR:
Título: {job_title}
Descripción: {job_description[:1000]}  # Limitar a 1000 chars para no exceder tokens

PERFILES DE CV DISPONIBLES:
{self.CV_CONTEXTS['software']}

{self.CV_CONTEXTS['engineer']}

RESPUESTA REQUERIDA (JSON):
{{
  "cv_type": "software" o "engineer",
  "confidence": 0.0-1.0,
  "reasoning": "explicación breve de por qué este CV es apropiado",
  "key_matches": ["skill1", "skill2", "skill3"]
}}"""
            
            # Llamar a OpenRouter
            response = self.client.call(
                message=user_message,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=500,
                expect_json=True
            )
            
            # Parsear respuesta
            result = self.client.extract_json_response(response)
            
            # Validar y extraer datos
            cv_type = result.get('cv_type', 'software')  # Default a software si falla
            confidence = result.get('confidence', 0.5)
            reasoning = result.get('reasoning', 'Selección automática basada en análisis de IA')
            
            # Validar cv_type
            if cv_type not in ['software', 'engineer']:
                logger.warning(f"cv_type inválido '{cv_type}', usando 'software' por defecto")
                cv_type = 'software'
                confidence = max(0.3, confidence - 0.2)  # Reducir confianza
            
            # Obtener ruta del CV según mapeo
            cv_path = self.CV_MAPPING.get((cv_type, language))
            
            if not cv_path:
                logger.error(f"No se encontró CV para tipo={cv_type}, idioma={language}")
                # Fallback a software en inglés
                cv_type = 'software'
                language = 'en'
                cv_path = self.CV_MAPPING[('software', 'en')]
                confidence = 0.3
                reasoning = "Fallback a CV por defecto debido a error en selección"
            
            # Verificar que el archivo existe
            if not os.path.exists(cv_path):
                logger.error(f"Archivo de CV no encontrado: {cv_path}")
                # Intentar con el otro CV
                alt_type = 'engineer' if cv_type == 'software' else 'software'
                alt_path = self.CV_MAPPING.get((alt_type, language))
                if alt_path and os.path.exists(alt_path):
                    logger.info(f"Usando CV alternativo: {alt_path}")
                    cv_type = alt_type
                    cv_path = alt_path
                    confidence = max(0.3, confidence - 0.3)
                else:
                    raise FileNotFoundError(f"No se encontró ningún CV válido")
            
            recommendation = CVRecommendation(
                cv_type=cv_type,
                language=language,
                cv_path=cv_path,
                confidence=confidence,
                reasoning=reasoning
            )
            
            logger.info(f"CV seleccionado: {cv_type} ({language}) - Confianza: {confidence:.2f}")
            logger.info(f"Ruta: {cv_path}")
            logger.info(f"Razón: {reasoning}")
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error al seleccionar CV: {e}")
            # Fallback a CV por defecto
            logger.info("Usando CV por defecto (software, inglés)")
            return CVRecommendation(
                cv_type='software',
                language='en',
                cv_path=self.CV_MAPPING[('software', 'en')],
                confidence=0.2,
                reasoning=f"Fallback debido a error: {str(e)}"
            )
    
    def detect_language(self, text: str) -> str:
        """
        Detecta el idioma del texto (inglés o español).
        
        Usa heurísticas simples basadas en palabras clave comunes.
        Si no puede determinar con certeza, asume inglés (más común en tech).
        
        Args:
            text: Texto a analizar (título + descripción)
            
        Returns:
            'en' para inglés, 'es' para español
        """
        text_lower = text.lower()
        
        # Palabras clave en español
        spanish_keywords = [
            'años', 'experiencia', 'requisitos', 'conocimientos', 'habilidades',
            'empresa', 'trabajo', 'puesto', 'equipo', 'desarrollo',
            'buscamos', 'necesitamos', 'ofrecemos', 'únete', 'postular'
        ]
        
        # Palabras clave en inglés
        english_keywords = [
            'years', 'experience', 'requirements', 'skills', 'knowledge',
            'company', 'work', 'position', 'team', 'development',
            'looking', 'seeking', 'we need', 'join', 'apply'
        ]
        
        # Contar coincidencias
        spanish_count = sum(1 for keyword in spanish_keywords if keyword in text_lower)
        english_count = sum(1 for keyword in english_keywords if keyword in text_lower)
        
        # Decidir idioma
        if spanish_count > english_count:
            logger.debug(f"Idioma detectado: español (score: {spanish_count} vs {english_count})")
            return 'es'
        else:
            logger.debug(f"Idioma detectado: inglés (score: {english_count} vs {spanish_count})")
            return 'en'
