"""
Modelos de datos para el sistema de automatización de postulaciones LinkedIn.

Este módulo define las estructuras de datos utilizadas en todo el sistema,
incluyendo campos de formulario, recomendaciones de CV, respuestas de IA,
decisiones de aplicación, y resultados de postulaciones.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from selenium.webdriver.remote.webelement import WebElement


@dataclass
class FormField:
    """
    Representa un campo del formulario de postulación.
    
    Attributes:
        element: WebElement de Selenium que representa el campo
        field_type: Tipo de campo (text, email, phone, dropdown, textarea, radio, checkbox, file)
        label: Etiqueta visible del campo
        purpose: Descripción del propósito del campo (ej: "years of experience")
        required: Indica si el campo es obligatorio
        options: Lista de opciones disponibles (solo para dropdowns)
    """
    element: WebElement
    field_type: str
    label: str
    purpose: str
    required: bool
    options: Optional[List[str]] = None


@dataclass
class CVRecommendation:
    """
    Recomendación de CV generada por la IA.
    
    Attributes:
        cv_type: Tipo de CV ('software' para Software Engineer o 'engineer' para Automatización/Data/IA)
        language: Idioma del CV ('en' para inglés o 'es' para español)
        cv_path: Ruta completa al archivo PDF del CV
        confidence: Nivel de confianza de la recomendación (0.0 a 1.0)
        reasoning: Explicación de por qué se seleccionó este CV
    """
    cv_type: str
    language: str
    cv_path: str
    confidence: float
    reasoning: str


@dataclass
class QuestionAnswer:
    """
    Respuesta a una pregunta del formulario generada por la IA.
    
    Attributes:
        question: Texto de la pregunta del formulario
        answer: Respuesta generada por la IA
        confidence: Nivel de confianza de la respuesta (0.0 a 1.0)
        reasoning: Explicación de cómo se llegó a la respuesta
        sources: Partes del CV utilizadas para generar la respuesta
        field_type: Tipo de campo al que corresponde la respuesta
    """
    question: str
    answer: str
    confidence: float
    reasoning: str
    sources: List[str]
    field_type: str


@dataclass
class ApplicationDecision:
    """
    Decisión sobre cómo proceder con una postulación.
    
    Attributes:
        action: Acción a tomar ('SUBMIT' para enviar automáticamente,
                'UNCERTAIN' para enviar pero marcar como inseguro,
                'MANUAL' para revisión manual)
        overall_confidence: Confianza general calculada de todas las respuestas
        reasoning: Explicación de la decisión tomada
        low_confidence_questions: Lista de preguntas con confianza por debajo del umbral
    """
    action: str
    overall_confidence: float
    reasoning: str
    low_confidence_questions: List[str]


@dataclass
class ProcessedJob:
    """
    Estado de un trabajo procesado (para persistencia).
    
    Attributes:
        url: URL del trabajo en LinkedIn
        status: Estado del procesamiento (APPLIED, MANUAL, NO_DISPONIBLE, ERROR, INSEGURO)
        timestamp: Fecha y hora del procesamiento
        cv_used: Nombre del CV utilizado (opcional)
        error_message: Mensaje de error si el procesamiento falló (opcional)
    """
    url: str
    status: str
    timestamp: datetime
    cv_used: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ApplicationResult:
    """
    Resultado completo de una postulación.
    
    Attributes:
        job_url: URL del trabajo en LinkedIn
        job_title: Título del puesto
        company: Nombre de la empresa
        status: Estado final (APPLIED, MANUAL, NO_DISPONIBLE, ERROR, INSEGURO)
        cv_used: Nombre del CV utilizado (opcional)
        questions_answered: Número de preguntas respondidas por la IA
        average_confidence: Confianza promedio de todas las respuestas
        notes: Notas adicionales sobre la postulación
        timestamp: Fecha y hora de la postulación
    """
    job_url: str
    job_title: str
    company: str
    status: str
    cv_used: Optional[str]
    questions_answered: int
    average_confidence: float
    notes: str
    timestamp: datetime
