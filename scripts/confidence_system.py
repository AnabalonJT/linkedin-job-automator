"""
Sistema de confianza para decisiones de auto-submit.

Este módulo evalúa la confianza de las respuestas generadas por IA y decide
si la postulación debe enviarse automáticamente, marcarse como insegura, o
requerir revisión manual.
"""

import logging
import os
from typing import List
from models import QuestionAnswer, ApplicationDecision

logger = logging.getLogger(__name__)


class ConfidenceSystem:
    """
    Sistema de confianza para decidir auto-submit vs manual review.
    
    Evalúa todas las respuestas de IA y decide la acción basándose en umbrales:
    - Alta confianza (≥ 0.85): SUBMIT automáticamente
    - Confianza media (0.65-0.85): UNCERTAIN (enviar pero marcar como inseguro)
    - Baja confianza (< 0.65): MANUAL (requiere revisión manual)
    """
    
    def __init__(self, high_threshold: float = None, low_threshold: float = None):
        """
        Inicializa el sistema de confianza.
        
        Args:
            high_threshold: Umbral alto de confianza (default: 0.85, configurable via env)
            low_threshold: Umbral bajo de confianza (default: 0.65, configurable via env)
        """
        # Cargar umbrales desde variables de entorno o usar defaults
        self.high_threshold = high_threshold or float(os.getenv('HIGH_THRESHOLD', '0.85'))
        self.low_threshold = low_threshold or float(os.getenv('LOW_THRESHOLD', '0.65'))
        
        logger.info(f"ConfidenceSystem inicializado: high={self.high_threshold}, low={self.low_threshold}")
    
    def evaluate_application(self, answers: List[QuestionAnswer]) -> ApplicationDecision:
        """
        Evalúa todas las respuestas y decide la acción.
        
        Lógica de decisión:
        - Si TODAS las respuestas tienen confidence ≥ high_threshold → SUBMIT
        - Si ALGUNA respuesta tiene confidence entre low_threshold y high_threshold → UNCERTAIN
        - Si ALGUNA respuesta tiene confidence < low_threshold → MANUAL
        
        Args:
            answers: Lista de respuestas con sus niveles de confianza
            
        Returns:
            ApplicationDecision con action (SUBMIT, UNCERTAIN, MANUAL), overall_confidence, reasoning, low_confidence_questions
        """
        if not answers:
            logger.warning("No hay respuestas para evaluar")
            return ApplicationDecision(
                action='MANUAL',
                overall_confidence=0.0,
                reasoning="No se generaron respuestas",
                low_confidence_questions=[]
            )
        
        logger.info(f"Evaluando {len(answers)} respuestas")
        
        # Calcular confianza general
        overall_confidence = self.calculate_overall_confidence(answers)
        
        # Identificar preguntas con baja confianza
        low_confidence_questions = []
        medium_confidence_questions = []
        
        for answer in answers:
            if answer.confidence < self.low_threshold:
                low_confidence_questions.append(answer.question)
            elif answer.confidence < self.high_threshold:
                medium_confidence_questions.append(answer.question)
        
        # Decidir acción
        if low_confidence_questions:
            # Si hay preguntas con confianza muy baja → MANUAL
            action = 'MANUAL'
            reasoning = f"Confianza muy baja en {len(low_confidence_questions)} pregunta(s). Requiere revisión manual."
            logger.info(f"Decisión: MANUAL - {len(low_confidence_questions)} preguntas con confianza < {self.low_threshold}")
            
        elif medium_confidence_questions:
            # Si hay preguntas con confianza media → UNCERTAIN
            action = 'UNCERTAIN'
            reasoning = f"Confianza media en {len(medium_confidence_questions)} pregunta(s). Se enviará pero se marcará como inseguro."
            logger.info(f"Decisión: UNCERTAIN - {len(medium_confidence_questions)} preguntas con confianza media")
            
        else:
            # Todas las preguntas tienen alta confianza → SUBMIT
            action = 'SUBMIT'
            reasoning = f"Alta confianza en todas las respuestas (promedio: {overall_confidence:.2f}). Se enviará automáticamente."
            logger.info(f"Decisión: SUBMIT - Todas las respuestas con confianza ≥ {self.high_threshold}")
        
        # Combinar todas las preguntas problemáticas
        all_low_confidence = low_confidence_questions + medium_confidence_questions
        
        decision = ApplicationDecision(
            action=action,
            overall_confidence=overall_confidence,
            reasoning=reasoning,
            low_confidence_questions=all_low_confidence
        )
        
        logger.info(f"Confianza general: {overall_confidence:.2f}")
        logger.info(f"Acción decidida: {action}")
        
        return decision
    
    def calculate_overall_confidence(self, answers: List[QuestionAnswer]) -> float:
        """
        Calcula confianza general como promedio ponderado.
        
        Todas las respuestas tienen el mismo peso por ahora. En el futuro se podría
        ponderar según la importancia de cada pregunta.
        
        Args:
            answers: Lista de respuestas con sus niveles de confianza
            
        Returns:
            Confianza promedio (0.0 a 1.0)
        """
        if not answers:
            return 0.0
        
        total_confidence = sum(answer.confidence for answer in answers)
        average_confidence = total_confidence / len(answers)
        
        return round(average_confidence, 2)
    
    def get_confidence_summary(self, answers: List[QuestionAnswer]) -> dict:
        """
        Genera un resumen de confianza para logging/debugging.
        
        Args:
            answers: Lista de respuestas
            
        Returns:
            Dict con estadísticas de confianza
        """
        if not answers:
            return {
                'total_questions': 0,
                'average_confidence': 0.0,
                'high_confidence_count': 0,
                'medium_confidence_count': 0,
                'low_confidence_count': 0
            }
        
        high_count = sum(1 for a in answers if a.confidence >= self.high_threshold)
        medium_count = sum(1 for a in answers if self.low_threshold <= a.confidence < self.high_threshold)
        low_count = sum(1 for a in answers if a.confidence < self.low_threshold)
        
        return {
            'total_questions': len(answers),
            'average_confidence': self.calculate_overall_confidence(answers),
            'high_confidence_count': high_count,
            'medium_confidence_count': medium_count,
            'low_confidence_count': low_count,
            'high_threshold': self.high_threshold,
            'low_threshold': self.low_threshold
        }
