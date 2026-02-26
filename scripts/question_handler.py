"""
Manejador de preguntas del formulario usando IA (OpenRouter).

Este módulo responde preguntas del formulario de postulación usando IA, con manejo
especial para preguntas comunes (años de experiencia, elegibilidad, salario, etc.).
"""

import logging
import json
import os
import re
from typing import Optional, List, Dict
from openrouter_client import OpenRouterClient
from models import QuestionAnswer

logger = logging.getLogger(__name__)


class QuestionHandler:
    """
    Responde preguntas del formulario usando IA y contexto del CV.
    
    Maneja preguntas especiales con respuestas predefinidas y usa IA para
    preguntas generales. Incluye sistema de confianza para determinar si
    la respuesta es suficientemente confiable.
    """
    
    # Contexto del CV para la IA (resumen de habilidades y experiencia)
    CV_CONTEXT = """
    PERFIL PROFESIONAL:
    José Tomás Anabalón - Ingeniero en Ciencias de la Computación
    
    EXPERIENCIA:
    - 4+ años desarrollo de software (2019-2025)
    - 5 años Python (scripting, automatización, Django, ML)
    - 3 años Ruby on Rails (desarrollo full stack, APIs RESTful)
    - 2 años automatización (n8n, Selenium, web scraping)
    - 2 años data engineering (Snowflake, ETL)
    - 3 años ML/AI (PyTorch, TensorFlow, modelos generativos, 1 año universidad + 1 año tesis + 1 año profesional)
    
    HABILIDADES TÉCNICAS:
    - Backend: Python, Ruby on Rails, Django, APIs RESTful
    - Frontend: JavaScript, Angular, HTML/CSS
    - Bases de datos: PostgreSQL, MySQL, Redis, Cassandra
    - Cloud/DevOps: AWS (S3, Lambda), Docker, Git
    - Automatización: n8n, Selenium, scripts Python
    - Data: Pandas, NumPy, Snowflake, ETL pipelines
    - ML/AI: PyTorch, TensorFlow, OpenAI, LangChain
    
    INFORMACIÓN PERSONAL:
    - Email: jtanabalon@miuandes.cl
    - Teléfono: +56983931281
    - Ubicación: Santiago, Chile
    - Inglés: Avanzado (C1) - TOEFL ITP, Cambridge FCE
    - Español: Nativo
    - Autorizado para trabajar en Chile: Sí
    - Requiere sponsorship: No
    - Disponibilidad: Inmediata
    
    PROYECTOS DESTACADOS:
    - MakiMotion: Sistema de gestión de pacientes (Django, PostgreSQL, producción)
    - Tesis: Comparación de modelos generativos (PyTorch, TensorFlow)
    - Bot LinkedIn: Automatización de postulaciones (n8n, Selenium, Google Sheets, telegram)
    """
    
    def __init__(self, api_key: str = None, common_answers_path: str = "config/respuestas_comunes.json"):
        """
        Inicializa el manejador de preguntas.
        
        Args:
            api_key: API key de OpenRouter (opcional, puede venir de env)
            common_answers_path: Ruta al archivo de respuestas comunes
        """
        self.client = OpenRouterClient(api_key=api_key)
        self.common_answers_path = common_answers_path
        self.common_answers = self._load_common_answers()
        logger.info("QuestionHandler inicializado")
    
    def _load_common_answers(self) -> Dict:
        """Carga el archivo de respuestas comunes."""
        try:
            with open(self.common_answers_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"No se pudo cargar respuestas comunes: {e}")
            return {}
    
    def answer_question(
        self,
        question: str,
        field_type: str,
        cv_context: str = None,
        available_options: Optional[List[str]] = None
    ) -> QuestionAnswer:
        """
        Responde una pregunta del formulario.
        
        Primero intenta con respuestas especiales predefinidas. Si no aplica,
        usa IA para generar la respuesta basándose en el CV.
        
        Args:
            question: Texto de la pregunta
            field_type: Tipo de campo (text, number, dropdown, etc)
            cv_context: Contexto del CV (opcional, usa default si no se provee)
            available_options: Opciones disponibles para dropdowns
            
        Returns:
            QuestionAnswer con answer, confidence, reasoning, sources, field_type
        """
        logger.info(f"Respondiendo pregunta: {question} (tipo: {field_type})")
        
        # Usar contexto por defecto si no se provee
        if not cv_context:
            cv_context = self.CV_CONTEXT
        
        # Intentar con preguntas especiales primero
        special_answer = self.handle_special_questions(question, field_type)
        if special_answer:
            logger.info(f"Usando respuesta especial: {special_answer.answer}")
            return special_answer
        
        # Si no es pregunta especial, usar IA
        try:
            system_prompt = """Eres un asistente HONESTO para postulaciones de trabajo.
Tu tarea es responder preguntas basándote ESTRICTAMENTE en el perfil del candidato.

REGLAS CRÍTICAS - DEBES SEGUIRLAS SIEMPRE:
1. USA SOLO información EXPLÍCITA que existe en el CV
2. Si una tecnología está listada pero NO tiene años de experiencia especificados, responde "0" o marca confidence como MUY BAJA (< 0.3)
3. NUNCA inventes o asumas años de experiencia
4. NUNCA uses "experiencia general en desarrollo de software" como razón para tecnologías específicas que NO están en el CV
5. Para preguntas numéricas, responde SOLO el número (sin unidades, sin texto adicional)
6. Para dropdowns con opciones disponibles, DEBES elegir EXACTAMENTE una de las opciones listadas. NO inventes respuestas.
7. Siempre responde en JSON válido
8. Sé EXTREMADAMENTE honesto: si no tienes información EXPLÍCITA, di "0" con baja confianza

EJEMPLOS DE HONESTIDAD:
- Si el CV dice "Python: 5 años" → responde "5" con alta confianza
- Si el CV solo menciona "Airflow" sin años → responde "0" con confianza 0.2
- Si el CV no menciona la tecnología → responde "0" con confianza 0.1
- Si pregunta "¿Tienes experiencia en Glue Lambda?" y NO está en el CV → responde "0" con confianza 0.9 y razón "NO tengo experiencia con glue lambda según CV"

FORMATO DE RESPUESTA:
{{
  "answer": "tu respuesta aquí",
  "confidence": 0.0-1.0,
  "reasoning": "por qué esta respuesta (sé específico sobre qué información usaste o por qué no tienes información)",
  "sources": ["fuente1", "fuente2"]
}}"""
            
            # Construir mensaje para la IA
            options_str = ""
            if available_options:
                options_str = f"\n\nOPCIONES DISPONIBLES:\n" + "\n".join([f"- {opt}" for opt in available_options])
            
            # Cargar cv_context desde JSON si está disponible
            if isinstance(cv_context, dict):
                # Convertir dict a string legible
                cv_context_str = json.dumps(cv_context, indent=2, ensure_ascii=False)
            else:
                cv_context_str = cv_context
            
            user_message = f"""CONTEXTO DEL CANDIDATO:
{cv_context_str}

PREGUNTA:
Tipo de campo: {field_type}
Pregunta: {question}
{options_str}

INSTRUCCIONES ESPECIALES:
- Si es campo numérico (number): responde SOLO el número, sin unidades ni texto
- Si es dropdown CON opciones disponibles: DEBES elegir EXACTAMENTE una de las opciones listadas arriba. NO inventes respuestas.
- Si es dropdown SIN opciones: responde basándote en el CV
- Si no tienes información clara: confidence < 0.5
- CRÍTICO: Para tecnologías como Airflow, Kubernetes, Spark, Glue, Lambda - si el CV dice "años: 0" o "nivel: None", responde "0" con alta confianza
- NUNCA uses "experiencia general" como razón para tecnologías específicas que no están en el CV

RESPONDE EN JSON:"""
            
            # Log del prompt completo para debugging (Bug 5 fix)
            logger.info("=" * 80)
            logger.info("LLAMADA A OPENROUTER API")
            logger.info("=" * 80)
            logger.info(f"SYSTEM PROMPT:\n{system_prompt}")
            logger.info("-" * 80)
            logger.info(f"USER MESSAGE:\n{user_message}")
            logger.info("=" * 80)
            
            # Llamar a OpenRouter
            response = self.client.call(
                message=user_message,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=500,
                expect_json=True
            )
            
            # Log de la respuesta completa (Bug 5 fix)
            logger.info("=" * 80)
            logger.info("RESPUESTA DE OPENROUTER API")
            logger.info("=" * 80)
            logger.info(f"RAW RESPONSE:\n{response}")
            logger.info("=" * 80)
            
            # Parsear respuesta
            result = self.client.extract_json_response(response)
            
            # Log del JSON parseado (Bug 5 fix)
            logger.info("JSON PARSEADO:")
            logger.info(json.dumps(result, indent=2, ensure_ascii=False))
            logger.info("=" * 80)
            
            # Validar y extraer datos
            answer = result.get('answer', '')
            confidence = result.get('confidence', 0.5)
            reasoning = result.get('reasoning', 'Respuesta generada por IA')
            sources = result.get('sources', ['CV context'])
            
            # Log del reasoning y campos extraídos (Bug 5 fix)
            logger.info(f"REASONING DEL MODELO: {reasoning}")
            logger.info(f"CONFIDENCE: {confidence}")
            logger.info(f"ANSWER: {answer}")
            
            # Validar formato de respuesta según tipo de campo
            if field_type in ['number', 'text_input_number']:
                # Para campos numéricos, asegurar que sea solo número
                answer = self._extract_number(answer)
                if not answer or not answer.isdigit():
                    logger.warning(f"Respuesta numérica inválida: {answer}")
                    confidence = max(0.3, confidence - 0.2)
            
            question_answer = QuestionAnswer(
                question=question,
                answer=answer,
                confidence=confidence,
                reasoning=reasoning,
                sources=sources,
                field_type=field_type
            )
            
            logger.info(f"Respuesta IA: {answer} (confianza: {confidence:.2f})")
            return question_answer
            
        except Exception as e:
            logger.error(f"Error al responder pregunta con IA: {e}")
            # Fallback a respuesta de baja confianza
            return QuestionAnswer(
                question=question,
                answer="",
                confidence=0.0,
                reasoning=f"Error al generar respuesta: {str(e)}",
                sources=[],
                field_type=field_type
            )
    
    def handle_special_questions(self, question: str, field_type: str) -> Optional[QuestionAnswer]:
        """
        Maneja preguntas especiales comunes con respuestas predefinidas.
        
        Preguntas especiales:
        - Años de experiencia (general o por tecnología)
        - Elegibilidad legal para trabajar
        - Sponsorship/visa
        - Salario
        - Información personal (email, teléfono, etc.)
        
        Args:
            question: Texto de la pregunta
            field_type: Tipo de campo
            
        Returns:
            QuestionAnswer si es pregunta especial, None si no
        """
        question_lower = question.lower()
        
        # 1. Años de experiencia
        if self._matches_pattern(question_lower, ['years', 'años', 'experience', 'experiencia']):
            return self._handle_experience_question(question, question_lower, field_type)
        
        # 2. Elegibilidad legal
        if self._matches_pattern(question_lower, ['legally eligible', 'authorized to work', 'autorizado para trabajar', 'permiso de trabajo']):
            return QuestionAnswer(
                question=question,
                answer="Yes" if 'yes' in question_lower or 'no' not in question_lower else "Sí",
                confidence=0.95,
                reasoning="Ciudadano chileno con autorización completa para trabajar",
                sources=["Información personal"],
                field_type=field_type
            )
        
        # 3. Sponsorship
        if self._matches_pattern(question_lower, ['require sponsorship', 'need visa', 'visa sponsorship', 'requiere sponsor', 'necesita visa']):
            return QuestionAnswer(
                question=question,
                answer="No",
                confidence=0.95,
                reasoning="Ciudadano chileno, no requiere sponsorship",
                sources=["Información personal"],
                field_type=field_type
            )
        
        # 4. Salario
        if self._matches_pattern(question_lower, ['salary', 'salario', 'renta', 'pretensiones', 'compensation', 'sueldo']):
            return QuestionAnswer(
                question=question,
                answer="1200000",
                confidence=0.95,
                reasoning="Expectativa salarial: 1.200.000 CLP mensuales",
                sources=["Información personal"],
                field_type=field_type
            )
        
        # 5. Email
        if self._matches_pattern(question_lower, ['email', 'correo', 'e-mail']):
            email = self.common_answers.get('informacion_personal', {}).get('email', 'jtanabalon@miuandes.cl')
            return QuestionAnswer(
                question=question,
                answer=email,
                confidence=1.0,
                reasoning="Email del candidato",
                sources=["Información personal"],
                field_type=field_type
            )
        
        # 6. Teléfono
        if self._matches_pattern(question_lower, ['phone', 'teléfono', 'telefono', 'celular', 'móvil']):
            phone = self.common_answers.get('informacion_personal', {}).get('telefono', '+56983931281')
            return QuestionAnswer(
                question=question,
                answer=phone,
                confidence=1.0,
                reasoning="Teléfono del candidato",
                sources=["Información personal"],
                field_type=field_type
            )
        
        # No es pregunta especial
        return None
    
    def _handle_experience_question(self, question: str, question_lower: str, field_type: str) -> QuestionAnswer:
        """Maneja preguntas sobre años de experiencia."""
        logger.info(f"Procesando pregunta de experiencia: {question}")
        
        # Buscar tecnología específica en la pregunta
        # IMPORTANTE: Listar SOLO tecnologías con años EXPLÍCITOS en el CV
        tech_experience = {
            'python': '5',
            'ruby': '3',
            'rails': '3',
            'django': '1',
            'javascript': '3',
            'angular': '3',
            'sql': '4',
            'docker': '2',
            'aws': '2',
            'machine learning': '3',
            'ml': '3',
            'ai': '3',
            'ia': '3',
            'inteligencia artificial': '3',
            'artificial intelligence': '3',
            'automatización': '2',
            'automation': '2',
            'data': '2',
            # Tecnologías con 0 años (NO tengo experiencia)
            'airflow': '0',
            'apache airflow': '0',
            'kubernetes': '0',
            'k8s': '0',
            'spark': '0',
            'apache spark': '0',
            'kafka': '0',
            'terraform': '0',
            'jenkins': '0',
            'mongodb': '0',
            'mongo': '0',
            'glue': '0',
            'aws glue': '0',
            'lambda': '0',
            'aws lambda': '0',
            'glue lambda': '0',
            'node.js': '1',
            'nodejs': '1',
            'node': '1'
        }
        
        # CRITICAL FIX: Ordenar tecnologías por longitud (más largas primero) para evitar substring matching incorrecto
        # Esto asegura que "airflow" se verifique antes que "ai", evitando coincidencias falsas
        sorted_techs = sorted(tech_experience.items(), key=lambda x: len(x[0]), reverse=True)
        logger.info(f"Tecnologías ordenadas (primeras 5): {[tech for tech, _ in sorted_techs[:5]]}")
        
        # Buscar coincidencias (priorizar coincidencias más largas primero)
        for tech, years in sorted_techs:
            if tech in question_lower:
                confidence = 0.95 if years != '0' else 0.90
                reasoning = f"Años de experiencia con {tech} según CV" if years != '0' else f"NO tengo experiencia con {tech} según CV"
                
                logger.info(f"✓ COINCIDENCIA ENCONTRADA: '{tech}' → {years} años")
                logger.info(f"  Pregunta contenía: '{tech}' en '{question_lower}'")
                
                return QuestionAnswer(
                    question=question,
                    answer=years,
                    confidence=confidence,
                    reasoning=reasoning,
                    sources=["Experiencia profesional"],
                    field_type=field_type
                )
        
        # Si no se encontró tecnología específica, usar experiencia general
        logger.info("No se encontró tecnología específica, usando experiencia general")
        return QuestionAnswer(
            question=question,
            answer="4",
            confidence=0.90,
            reasoning="Años de experiencia general en desarrollo de software",
            sources=["Experiencia profesional"],
            field_type=field_type
        )
    
    def _matches_pattern(self, text: str, patterns: List[str]) -> bool:
        """Verifica si el texto coincide con alguno de los patrones."""
        return any(pattern in text for pattern in patterns)
    
    def _extract_number(self, text: str) -> str:
        """Extrae solo el número de un texto."""
        # Buscar primer número en el texto
        match = re.search(r'\d+', str(text))
        if match:
            return match.group()
        return text
