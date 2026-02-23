"""
Clasificador IA - Integración de OpenRouter + CV Context

Proporciona métodos para:
1. Clasificar trabajos (tipos, match %, recomendación CV)
2. Responder preguntas de postulación (con confianza)
3. Gestión de confianza y auto-submit
"""

import os
import json
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum

from openrouter_client import OpenRouterClient, AIResponse
from cv_processor import CVProcessor, CVContext


class ConfidenceLevel(Enum):
    """Niveles de confianza para decisiones"""
    VERY_LOW = 0.3  # < 30% - casi nunca automático
    LOW = 0.5        # 30-50% - manual
    MEDIUM = 0.7     # 50-70% - borderline
    HIGH = 0.85      # 70-85% - automático (threshold)
    VERY_HIGH = 0.95 # 85-100% - muy automático


class AIClassifier:
    """Clasificador IA con contexto del candidato"""
    
    def __init__(
        self,
        cv_contexts: Optional[Dict[str, str]] = None,
        confidence_threshold: float = 0.85,
        api_key: Optional[str] = None
    ):
        """
        Inicializar clasificador
        
        Args:
            cv_contexts: Dict con {software: contexto_string, engineer: contexto_string}
            confidence_threshold: Umbral mínimo para auto-respuesta (default: 0.85)
            api_key: API key OpenRouter (si no se proporciona, viene del env)
        """
        self.confidence_threshold = confidence_threshold
        self.debug = os.getenv('DEBUG', 'False').lower() == 'true'
        
        # Inicializar cliente OpenRouter
        self.ai_client = OpenRouterClient(api_key=api_key)
        
        # Cargar contexto CV (ahora unificado, siempre el mismo)
        if cv_contexts and isinstance(cv_contexts, dict):
            self.cv_context = cv_contexts.get('unified') or cv_contexts.get('software', '')
            if self.debug:
                print(f"📋 CV Context cargado desde parámetro")
        else:
            # Cargar desde processor
            cv_processor = CVProcessor()
            context_obj = cv_processor.load_or_create()
            self.cv_context = cv_processor.get_context_as_string(context_obj)
            if self.debug:
                print(f"📋 CV Context cargado desde CVProcessor")
                print(f"   Caracteres: {len(self.cv_context)}")
        
        # Stats
        self.stats = {
            'total_classifications': 0,
            'total_questions': 0,
            'auto_answered': 0,
            'manual_questions': 0,
            'average_confidence': 0.0
        }
        self.confidences = []
    
    def set_cv_type(self, cv_type: str) -> None:
        """
        Deprecated: Ya no aplicable (contexto único)
        Se mantiene para compatibilidad con código existente
        """
        if self.debug:
            print(f"⚠️  set_cv_type() deprecated - usando contexto unificado")
    
    def get_current_cv_context(self) -> str:
        """Obtiene el contexto CV actual (unificado)"""
        return self.cv_context
    
    def classify_job(
        self,
        job_title: str,
        job_description: str,
        job_requirements: str,
        job_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Clasificar un trabajo
        
        Args:
            job_title: Título del trabajo
            job_description: Descripción del trabajo
            job_requirements: Requisitos del trabajo
            job_url: URL del trabajo (opcional, para logs)
        
        Returns:
            Dict con:
            - job_type: "software|consultoria|otro"
            - match_percentage: 0-100
            - confidence: 0.0-1.0
            - recommended_cv: "software|engineer"
            - reasoning: explicación
            - top_matching_skills: lista
            - missing_skills: lista
            - auto_submit: boolean (si >= threshold)
        """
        
        if self.debug:
            print(f"\n🏢 Clasificando trabajo: {job_title}")
            print(f"   Descripción (primeros 300 chars): {job_description[:300]}")
            print(f"   CV Context (primeros 200 chars): {self.get_current_cv_context()[:200]}")
        
        try:
            # Llamar IA con CV context actual
            result = self.ai_client.classify_job(
                job_title=job_title,
                job_description=job_description,
                job_requirements=job_requirements,
                cv_context=self.get_current_cv_context()
            )
            
            if self.debug:
                print(f"   🤖 Respuesta IA RAW: {result}")
            
            # Validar respuesta
            if not result or not isinstance(result, dict):
                if self.debug:
                    print(f"   ⚠️  Respuesta IA inválida, clasificación manual")
                return self._default_classification(job_title)
            
            # Extraer confianza
            confidence = result.get('confidence', 0.5)
            confidence = float(confidence) if confidence else 0.5
            confidence = max(0.0, min(1.0, confidence))  # Clamp 0-1
            
            # Mapear recomendación de CV (software o consultoria → engineer)
            recommended_cv = result.get('recommended_cv', 'software')
            if recommended_cv in ['consultoria', 'engineer', 'data', 'analytics']:
                result['recommended_cv'] = 'engineer'
            else:
                result['recommended_cv'] = 'software'  # Default fallback
            
            # Agregar auto_submit
            result['auto_submit'] = confidence >= self.confidence_threshold
            
            # Agregar razonamiento fallback
            if not result.get('reasoning'):
                result['reasoning'] = "Clasificación automática"
            
            # Stats
            self.stats['total_classifications'] += 1
            self.confidences.append(confidence)
            self._update_avg_confidence()
            
            if self.debug:
                print(f"   ✅ {result.get('job_type', 'unknown')} - Match: {result.get('match_percentage', 0)}%")
                print(f"   🎯 Confianza: {confidence:.2%}")
                print(f"   📋 CV Recomendado: {result.get('recommended_cv', 'software')}")
                if result['auto_submit']:
                    print(f"   🚀 Auto-submit HABILITADO")
            
            return result
        
        except Exception as e:
            if self.debug:
                print(f"   ❌ Error en clasificación: {str(e)}")
            return self._default_classification(job_title)
    
    def answer_question(
        self,
        question_text: str,
        question_type: str = "text",
        options: Optional[List[str]] = None,
        previous_answers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Responder pregunta de postulación
        
        Args:
            question_text: Texto de la pregunta
            question_type: "text", "boolean", "single_choice", "multiple_choice"
            options: Opciones (si aplica)
            previous_answers: Respuestas previas (para coherencia)
        
        Returns:
            Dict con:
            - answer: la respuesta
            - confidence: 0.0-1.0
            - reasoning: por qué
            - sources: dónde viene la info (CV skills, experience, etc)
            - auto_submit: boolean (si >= threshold)
            - answer_type: "text|selected_option"
            - marked_as_manual: si confianza < threshold
        """
        
        if self.debug:
            print(f"\n❓ Respondiendo pregunta: {question_text[:60]}...")
        
        try:
            # Llamar IA con CV context actual
            result = self.ai_client.answer_question(
                question_text=question_text,
                question_type=question_type,
                options=options,
                cv_context=self.get_current_cv_context(),
                previous_answers=previous_answers
            )
            
            # Validar respuesta
            if not result or not isinstance(result, dict):
                if self.debug:
                    print(f"   ⚠️  Respuesta IA inválida")
                return self._default_answer("Información no disponible en CV")
            
            # Extraer confianza
            confidence = result.get('confidence', 0.5)
            confidence = float(confidence) if confidence else 0.5
            confidence = max(0.0, min(1.0, confidence))  # Clamp 0-1
            
            # Decidir si auto-submit
            auto_submit = confidence >= self.confidence_threshold
            
            # Si es single/multiple choice y tenemos opciones, verificar que la respuesta esté en opciones
            if question_type in ['single_choice', 'multiple_choice'] and options:
                answer = result.get('answer', '')
                if answer not in options and auto_submit:
                    if self.debug:
                        print(f"   ⚠️  Respuesta no en opciones. Reduciendo confianza")
                    confidence = confidence * 0.8  # Penalizar
                    auto_submit = confidence >= self.confidence_threshold
            
            # Enriquecer resultado
            result['confidence'] = confidence
            result['auto_submit'] = auto_submit
            result['marked_as_manual'] = not auto_submit
            result['answer_type'] = 'selected_option' if question_type in ['single_choice', 'multiple_choice'] else 'text'
            
            # Stats
            self.stats['total_questions'] += 1
            if auto_submit:
                self.stats['auto_answered'] += 1
            else:
                self.stats['manual_questions'] += 1
            self.confidences.append(confidence)
            self._update_avg_confidence()
            
            if self.debug:
                print(f"   💭 Respuesta: {result.get('answer', 'N/A')[:50]}")
                print(f"   🎯 Confianza: {confidence:.2%}")
                if result.get('reasoning'):
                    print(f"   📌 Razón: {result['reasoning'][:60]}")
                if auto_submit:
                    print(f"   🚀 Auto-submit: SÍ")
                else:
                    print(f"   ⏸️  Manual requerido")
            
            return result
        
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"❌ Error en answer_question: {error_msg}")
            print(f"Traceback: {traceback.format_exc()}")
            if self.debug:
                print(f"   ❌ Error respondiendo: {error_msg}")
            return self._default_answer(f"Error: {error_msg}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de clasificación"""
        avg_confidence = self._calculate_avg_confidence()
        
        return {
            'total_classifications': self.stats['total_classifications'],
            'total_questions': self.stats['total_questions'],
            'auto_answered': self.stats['auto_answered'],
            'manual_questions': self.stats['manual_questions'],
            'average_confidence': round(avg_confidence, 3),
            'automation_rate': round(
                (self.stats['auto_answered'] / max(1, self.stats['total_questions'])) * 100,
                1
            ) if self.stats['total_questions'] > 0 else 0,
            'threshold': self.confidence_threshold
        }
    
    def reset_stats(self) -> None:
        """Reinicia estadísticas"""
        self.stats = {
            'total_classifications': 0,
            'total_questions': 0,
            'auto_answered': 0,
            'manual_questions': 0,
            'average_confidence': 0.0
        }
        self.confidences = []
    
    # ======================== Métodos Auxiliares ========================
    
    def _default_classification(self, job_title: str) -> Dict[str, Any]:
        """Clasificación por defecto cuando IA falla"""
        return {
            'job_type': 'software',
            'match_percentage': 50,
            'confidence': 0.3,
            'reasoning': 'IA no disponible, clasificación por defecto',
            'recommended_cv': 'software',
            'top_matching_skills': [],
            'missing_skills': [],
            'auto_submit': False
        }
    
    def _default_answer(self, message: str = "Información no disponible en CV") -> Dict[str, Any]:
        """Respuesta por defecto cuando IA falla"""
        return {
            'answer': message,
            'confidence': 0.1,
            'reasoning': 'IA no disponible, marcado como manual',
            'sources': [],
            'auto_submit': False,
            'answer_type': 'text',
            'marked_as_manual': True
        }
    
    def _update_avg_confidence(self) -> None:
        """Actualiza confianza promedio"""
        if self.confidences:
            self.stats['average_confidence'] = sum(self.confidences) / len(self.confidences)
    
    def _calculate_avg_confidence(self) -> float:
        """Calcula confianza promedio"""
        if not self.confidences:
            return 0.0
        return sum(self.confidences) / len(self.confidences)
    
    def extract_best_option(
        self,
        options: List[str],
        question_text: str
    ) -> Tuple[str, float]:
        """
        Extrae la mejor opción de múltiple choice
        
        Args:
            options: Lista de opciones
            question_text: Texto de la pregunta
        
        Returns:
            Tupla (opción seleccionada, confianza)
        """
        system_prompt = """Eres un experto en seleccionar la mejor opción de múltiple choice.
        
Dado el contexto del candidato y la pregunta, elige la mejor opción.
Responde en JSON con {selected: "opción", confidence: 0.0-1.0}"""
        
        user_message = f"""PREGUNTA: {question_text}

CONTEXTO: {self.get_current_cv_context()}

OPCIONES:
{chr(10).join([f'{i+1}. {opt}' for i, opt in enumerate(options)])}

Elige la mejor opción."""
        
        try:
            response = self.ai_client.call(
                message=user_message,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=200,
                expect_json=True
            )
            result = self.ai_client.extract_json_response(response)
            selected = result.get('selected', options[0])
            confidence = float(result.get('confidence', 0.5))
            return (selected, confidence)
        except:
            return (options[0], 0.3)
    
    def evaluate_answer_quality(
        self,
        question: str,
        answer: str
    ) -> Dict[str, Any]:
        """
        Evalúa la calidad de una respuesta
        
        Args:
            question: Pregunta original
            answer: Respuesta propuesta
        
        Returns:
            Dict con evaluación y sugerencias
        """
        system_prompt = "Eres un evaluador de respuestas de postulación. Evalúa si la respuesta es apropiada."
        
        user_message = f"""PREGUNTA: {question}
RESPUESTA PROPUESTA: {answer}
CONTEXTO: {self.get_current_cv_context()}

Evalúa (JSON):
{{
  "is_appropriate": boolean,
  "quality_score": 0-1,
  "issues": ["issue1", ...],
  "suggestions": ["suggestion1", ...]
}}"""
        
        try:
            response = self.ai_client.call(
                message=user_message,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=300,
                expect_json=True
            )
            return self.ai_client.extract_json_response(response)
        except:
            return {
                'is_appropriate': True,
                'quality_score': 0.5,
                'issues': [],
                'suggestions': []
            }


# Ejemplo de uso
if __name__ == "__main__":
    os.environ['DEBUG'] = 'True'
    
    try:
        # Inicializar
        classifier = AIClassifier(confidence_threshold=0.85)
        
        print("\n=== TEST 1: Clasificación ===")
        result = classifier.classify_job(
            job_title="Senior Backend Engineer",
            job_description="We need a Python expert...",
            job_requirements="Python, Django, PostgreSQL, AWS"
        )
        print(json.dumps(result, indent=2))
        
        print("\n=== TEST 2: Respuesta Pregunta ===")
        answer = classifier.answer_question(
            question_text="Explica tu experiencia con Docker",
            question_type="text"
        )
        print(json.dumps(answer, indent=2))
        
        print("\n=== TEST 3: Pregunta Multiple Choice ===")
        answer = classifier.answer_question(
            question_text="¿Cuál prefieres?",
            question_type="single_choice",
            options=["Option A", "Option B", "Option C"]
        )
        print(json.dumps(answer, indent=2))
        
        print("\n=== ESTADÍSTICAS ===")
        stats = classifier.get_stats()
        print(json.dumps(stats, indent=2))
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
