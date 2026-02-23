"""
Cliente para OpenRouter API (Modelos de IA gratis)

Proporciona comunicación con modelos de IA gratuitos via OpenRouter
- Llama-2-7B (recomendado)
- Fallback automático a otros modelos
- Manejo de errores y reintentos
"""

import os
import json
import requests
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class ModelType(Enum):
    """Modelos disponibles en OpenRouter (gratuitos)"""
    # Modelos gratuitos verificados (Feb 2026)
    NVIDIA_NEMOTRON = "nvidia/nemotron-3-nano-30b-a3b:free"  # Bueno para clasificación
    STEPFUN_FLASH = "stepfun/step-3.5-flash:free"  # Rápido y eficiente
    QWEN_VL = "qwen/qwen3-vl-30b-a3b-thinking"  # Bueno para razonamiento
    LLAMA_3_70B = "meta-llama/llama-3.3-70b-instruct:free"  # Más potente pero puede no estar disponible
    
    # Usar Nvidia Nemotron como default
    AUTO = NVIDIA_NEMOTRON

@dataclass
class AIResponse:
    """Respuesta estructurada de la IA"""
    content: str
    model_used: str
    tokens_used: int
    confidence: Optional[float] = None
    parsed_json: Optional[Dict[str, Any]] = None
    raw_response: Optional[Dict[str, Any]] = None
    
    def __repr__(self):
        return f"AIResponse(model={self.model_used}, tokens={self.tokens_used}, confidence={self.confidence})"


class OpenRouterClient:
    """Cliente para llamadas a OpenRouter API"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = ModelType.AUTO.value):
        """
        Inicializar cliente OpenRouter
        
        Args:
            api_key: API key de OpenRouter (puede venir de env OPENROUTER_API_KEY)
            model: Modelo a usar (default: StepFun Step 3.5 Flash Free)
        """
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY no configurado. Configura la variable de entorno.")
        
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = model
        self.timeout = 30
        self.max_retries = 3
        self.retry_delay = 2
        
        # Headers para OpenRouter
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/linkedin-automator",
            "X-Title": "LinkedIn Job Automator",
            "Content-Type": "application/json"
        }
        
        # Logger simulado (se usará el logger real del proyecto después)
        self.debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    def call(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        expect_json: bool = False,
        fallback_to_auto: bool = True
    ) -> AIResponse:
        """
        Llamar a OpenRouter API
        
        Args:
            message: Mensaje del usuario
            system_prompt: Prompt del sistema (instrucciones)
            temperature: Creatividad (0.0-1.0). Bajo = determinístico
            max_tokens: Máximo de tokens en respuesta
            expect_json: Si True, parse la respuesta como JSON
            fallback_to_auto: Si True, intenta con "openrouter/auto" si falla
        
        Returns:
            AIResponse con contenido, modelo usado, tokens, etc.
        """
        
        messages = []
        
        # Agregar system prompt si existe
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Agregar mensaje del usuario
        messages.append({
            "role": "user",
            "content": message
        })
        
        # Intentar llamada
        for attempt in range(self.max_retries):
            try:
                if self.debug:
                    print(f"🔍 [OpenRouter] Intento {attempt + 1}/{self.max_retries}")
                    print(f"   Modelo: {self.model}")
                    print(f"   Tokens max: {max_tokens}")
                
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                
                # Llamar API
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                # Verificar status code
                if response.status_code == 429:
                    # Rate limit - esperar y reintentar
                    if self.debug:
                        print(f"⏱️  Rate limit. Esperando {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                    continue
                
                if response.status_code == 503:
                    # Servicio no disponible - intentar con auto
                    if fallback_to_auto and self.model != ModelType.AUTO.value:
                        if self.debug:
                            print(f"⚠️  Modelo {self.model} no disponible. Intentando con auto...")
                        self.model = ModelType.AUTO.value
                        return self.call(message, system_prompt, temperature, max_tokens, expect_json, fallback_to_auto=False)
                    else:
                        raise Exception(f"Modelo no disponible y fallback deshabilitado")
                
                if response.status_code != 200:
                    error_data = response.json()
                    raise Exception(f"OpenRouter error {response.status_code}: {error_data}")
                
                # Parsear respuesta
                data = response.json()
                
                if self.debug:
                    print(f"✅ Respuesta recibida")
                    print(f"   Status: {response.status_code}")
                    print(f"   Modelo usado: {data.get('model', 'desconocido')}")
                    print(f"   Tokens utilizados: {data.get('usage', {}).get('total_tokens', 0)}")
                
                # Validar estructura de la respuesta
                if 'choices' not in data or not data['choices']:
                    error_msg = f"Formato inválido de respuesta OpenRouter"
                    if 'error' in data:
                        error_msg += f": {data['error']}"
                    if self.debug:
                        print(f"❌ {error_msg}")
                        print(f"   Respuesta: {json.dumps(data)[:200]}...")
                    raise Exception(error_msg)
                
                # Extraer contenido
                try:
                    content = data['choices'][0]['message']['content']
                except (KeyError, IndexError, TypeError) as e:
                    error_msg = f"Error extrayendo contenido de respuesta: {str(e)}"
                    if self.debug:
                        print(f"❌ {error_msg}")
                        print(f"   Estructura de datos: {json.dumps(data)[:200]}...")
                    raise Exception(error_msg)
                
                model_used = data.get('model', self.model)
                tokens_used = data.get('usage', {}).get('total_tokens', 0)
                
                if self.debug:
                    print(f"   Contenido extraído correctamente ({len(content)} chars)")
                    print(f"   Primeros 300 chars: {content[:300]}")
                
                # Parsear JSON si se espera
                parsed_json = None
                confidence = None
                
                if expect_json:
                    try:
                        # Intentar parsear JSON del contenido
                        parsed_json = json.loads(content)
                        confidence = parsed_json.get('confidence', None)
                        
                        if self.debug:
                            print(f"   JSON parseado correctamente")
                            if confidence:
                                print(f"   Confianza IA: {confidence}")
                            # Mostrar keys del JSON
                            print(f"   Keys en JSON: {list(parsed_json.keys())}")
                    except json.JSONDecodeError as e:
                        if self.debug:
                            print(f"   ⚠️  No se pudo parsear JSON: {str(e)}")
                            print(f"   Contenido: {content[:200]}...")
                        # Marcar como error pero continuar
                        pass
                
                return AIResponse(
                    content=content,
                    model_used=model_used,
                    tokens_used=tokens_used,
                    confidence=confidence,
                    parsed_json=parsed_json,
                    raw_response=data
                )
            
            except requests.exceptions.Timeout:
                if self.debug:
                    print(f"⏱️  Timeout en intento {attempt + 1}. Reintentando...")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise
            
            except requests.exceptions.ConnectionError as e:
                if self.debug:
                    print(f"❌ Error de conexión: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise
            
            except Exception as e:
                if self.debug:
                    print(f"❌ Error: {str(e)}")
                raise
        
        raise Exception(f"Falló después de {self.max_retries} intentos")
    
    def extract_json_response(self, response: AIResponse) -> Dict[str, Any]:
        """
        Extraer JSON de una respuesta
        
        Args:
            response: AIResponse de call()
        
        Returns:
            Dict con JSON parseado, o {} si falla
        """
        if response.parsed_json:
            return response.parsed_json
        
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            if self.debug:
                print(f"⚠️  No se pudo extraer JSON de: {response.content[:100]}")
            return {}
    
    def classify_job(
        self,
        job_title: str,
        job_description: str,
        job_requirements: str,
        cv_context: str
    ) -> Dict[str, Any]:
        """
        Clasificar trabajo usando IA
        
        Args:
            job_title: Título del trabajo
            job_description: Descripción del trabajo
            job_requirements: Requisitos del trabajo
            cv_context: Contexto del CV del candidato (JSON string o resumen)
        
        Returns:
            Dict con clasificación, match %, confianza, etc.
        """
        
        system_prompt = """Eres un experto en recursos humanos y reclutamiento.
Tu tarea es clasificar ofertas de trabajo y evaluarlas contra el perfil del candidato.

REGLAS IMPORTANTES:
1. Siempre responde en JSON válido
2. Incluye siempre un campo "confidence" (0.0 a 1.0)
3. Sé conciso pero preciso
4. Si no tienes información clara, reduce la confianza"""
        
        user_message = f"""CONTEXTO DEL CANDIDATO:
{cv_context}

TRABAJO A CLASIFICAR:
Título: {job_title}
Descripción: {job_description}
Requisitos: {job_requirements}

RESPUESTA REQUERIDA (JSON):
{{
  "job_type": "software|consultoria|otro",
  "match_percentage": 0-100,
  "confidence": 0.0-1.0,
  "reasoning": "explicación breve",
  "recommended_cv": "software|consultoria",
  "top_matching_skills": ["skill1", "skill2"],
  "missing_skills": ["skill1"]
}}"""
        
        response = self.call(
            message=user_message,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=800,  # Aumentado de 500 a 800 para respuestas completas
            expect_json=True
        )
        
        return self.extract_json_response(response)
    
    def answer_question(
        self,
        question_text: str,
        question_type: str,
        options: Optional[List[str]],
        cv_context: str,
        previous_answers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Responder pregunta de postulación usando IA
        
        Args:
            question_text: Texto de la pregunta
            question_type: "text", "boolean", "single_choice", "multiple_choice"
            options: Opciones (si aplica)
            cv_context: Contexto del CV del candidato
            previous_answers: Respuestas previas (para coherencia)
        
        Returns:
            Dict con respuesta, confianza, razonamiento, etc.
        """
        
        system_prompt = """Eres un asistente para postulaciones de trabajo.
Tu tarea es responder preguntas basándose en el perfil del candidato.

REGLAS:
1. Usa solo información que existe en el CV
2. Si no tienes información, marca confidence como baja (< 0.5)
3. Para multiple choice, elige opciones que aparezcan en el CV o la mejor opcion
4. Siempre responde en JSON
5. Sé honesto: si no sabes, di que no tienes información

TIPOS DE PREGUNTA/RESPUESTA:
- text_input_number: RESPONDO SOLO UN NÚMERO (sin texto, sin decimales)
  Ejemplo: "3" o "5" (no "3 años" o "3.5")
- text_input_date: RESPONDO SOLO UNA FECHA
- text_input_email: RESPONDO SOLO UN EMAIL
- text_input_tel: RESPONDO UNO UN TELÉFONO  
- text_input: Texto libre
- text: Pregunta abierta

NOTAS ESPECIALES:

- Preguntas sobre elegibilidad / autorización:
  * Si pregunta "legally eligible" o "do not sponsor" -> "Yes" (0.95+ confianza)
  * El candidato está legalmente autorizado en Chile

- Preguntas NUMBER sobre "años de experiencia":
  * BUSCO EN: Skills section (con "years"), Experience section
  * RESPONDO SIEMPRE UN NÚMERO ENTERO SIN UNIDADES
  * Si no hay info -> "0" pero confianza baja
  * NO respondo "0.2" ni "3.5" - SÖ NÚMEROS ENTEROS
  * REST APIs (5 años) -> respuesta "5"
  * Python (4 años) -> respuesta "4"
  * Salesforce (no en CV) -> respuesta "0"

- Si pregunta "CV en inglés":
  * Responder "Sí" (0.9+ confianza)
  * CV tiene versión en inglés"""
        
        # Construir opciones string
        options_str = ""
        if options:
            options_str = "\nOPCIONES:\n" + "\n".join([f"- {opt}" for opt in options])
        
        # Construir respuestas previas string
        previous_str = ""
        if previous_answers:
            previous_str = "\nRESPUESTAS PREVIAS (para mantener coherencia):\n"
            for q, a in previous_answers.items():
                previous_str += f"- P: {q}\n  R: {a}\n"
        
        user_message = f"""CONTEXTO DEL CANDIDATO:
{cv_context}

{previous_str}

NUEVA PREGUNTA:
Tipo: {question_type}
Pregunta: {question_text}
{options_str}

RESPUESTA REQUERIDA (JSON):
{{
  "answer": "tu respuesta aquí",
  "confidence": 0.0-1.0,
  "reasoning": "por qué esta respuesta",
  "sources": ["source1", "source2"],
  "auto_submit": boolean
}}"""
        
        response = self.call(
            message=user_message,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=600,  # Aumentado de 500 a 600
            expect_json=True
        )
        
        return self.extract_json_response(response)
    
    def test_connection(self) -> bool:
        """Prueba la conexión con OpenRouter API"""
        try:
            if self.debug:
                print(f"🔍 Probando conexión con OpenRouter...")
            
            response = self.call(
                message="Responde en una palabra: ¿estás funcionando?",
                temperature=0.5,
                max_tokens=10
            )
            
            if self.debug:
                print(f"✅ Conexión exitosa")
                print(f"   Modelo: {response.model_used}")
                print(f"   Respuesta: {response.content}")
            
            return True
        except Exception as e:
            if self.debug:
                print(f"❌ Error en conexión: {str(e)}")
            return False


# Ejemplo de uso
if __name__ == "__main__":
    # Activar debug
    os.environ['DEBUG'] = 'True'
    
    try:
        client = OpenRouterClient()
        
        # Test básico
        print("\n=== TEST 1: Conexión ===")
        if client.test_connection():
            print("✅ Conexión OK")
        else:
            print("❌ Conexión FALLÓ")
        
        # Test clasificación
        print("\n=== TEST 2: Clasificación ===")
        result = client.classify_job(
            job_title="Senior Backend Engineer",
            job_description="We need a Python expert for our backend team. 5+ years required.",
            job_requirements="Python, Django, PostgreSQL, AWS",
            cv_context="Senior Backend Engineer with 6 years Python, Django, PostgreSQL experience"
        )
        print(json.dumps(result, indent=2))
        
        # Test respuesta pregunta
        print("\n=== TEST 3: Respuesta a Pregunta ===")
        answer = client.answer_question(
            question_text="¿Cuántos años de experiencia tienes con Python?",
            question_type="text",
            options=None,
            cv_context="6 años de experiencia con Python en proyectos Fintech"
        )
        print(json.dumps(answer, indent=2))
    
    except Exception as e:
        print(f"❌ Error: {e}")
