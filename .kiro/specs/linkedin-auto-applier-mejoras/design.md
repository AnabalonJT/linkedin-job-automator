# Documento de Diseño: Mejoras al Sistema de Automatización de Postulaciones LinkedIn

## Overview

Este documento describe el diseño técnico para mejorar el sistema automatizado de postulaciones en LinkedIn. El sistema actual (`linkedin_applier.py`) tiene limitaciones críticas en la interacción con el modal de postulación que aparece después de hacer clic en "Solicitud sencilla". Las mejoras propuestas incluyen:

- Detección robusta del modal usando JavaScript y múltiples selectores fallback
- Integración con IA (OpenRouter) para selección inteligente de CV y respuesta automática a preguntas
- Sistema de confianza para determinar cuándo enviar automáticamente vs. marcar para revisión manual
- Manejo robusto de errores, logging detallado y recuperación de estado

El sistema mantiene su arquitectura existente basada en:
- **n8n**: Orquestación del flujo de trabajo
- **Selenium WebDriver**: Automatización del navegador
- **Google Sheets**: Tracking de postulaciones
- **Telegram**: Notificaciones consolidadas
- **OpenRouter**: Servicios de IA para clasificación y respuestas

### Objetivos de Diseño

1. **Robustez**: Manejar cambios en la estructura HTML de LinkedIn mediante múltiples selectores fallback
2. **Inteligencia**: Usar IA para seleccionar CV apropiado y responder preguntas del formulario
3. **Confiabilidad**: Sistema de confianza para evitar respuestas incorrectas
4. **Observabilidad**: Logging detallado y screenshots para debugging
5. **Recuperabilidad**: Mantener estado para continuar después de interrupciones

## Architecture

### Componentes del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                           n8n Workflow                           │
│                    (Orquestación Principal)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    linkedin_applier.py                           │
│                  (LinkedInApplier Class)                         │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │  Modal Detector  │  │  Form Processor  │  │  CV Selector  │ │
│  │  (JavaScript)    │  │  (Field Handler) │  │  (AI-based)   │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │ Question Handler │  │ Confidence System│  │ State Manager │ │
│  │  (AI-powered)    │  │  (Threshold)     │  │  (Recovery)   │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
└───────┬──────────────────────┬──────────────────────┬───────────┘
        │                      │                      │
        ▼                      ▼                      ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  OpenRouter  │      │ Google Sheets│      │   Telegram   │
│  (IA API)    │      │  (Tracking)  │      │(Notificación)│
└──────────────┘      └──────────────┘      └──────────────┘
```

### Flujo de Datos Principal

1. **n8n** lee trabajos de Google Sheets y llama a `linkedin_applier.py`
2. **linkedin_applier.py** navega a la URL del trabajo
3. **Modal Detector** detecta si el trabajo está disponible y hace clic en "Solicitud sencilla"
4. **Modal Detector** espera y detecta el modal usando JavaScript
5. **Form Processor** identifica campos del formulario dentro del modal
6. **CV Selector** consulta OpenRouter para seleccionar el CV apropiado
7. **Question Handler** consulta OpenRouter para responder preguntas del formulario
8. **Confidence System** evalúa si la confianza es suficiente para auto-submit
9. **State Manager** actualiza Google Sheets con el resultado
10. **Telegram** recibe notificación consolidada al final del proceso

### Decisiones Arquitectónicas

#### 1. JavaScript como Método Primario de Interacción

**Decisión**: Usar `driver.execute_script()` como método primario para detectar y rellenar el modal, con Selenium como fallback.

**Razón**: El modal de LinkedIn se carga dinámicamente con JavaScript. Los métodos tradicionales de Selenium (`find_element`, `WebDriverWait`) pueden fallar porque el modal no está en el DOM inicial. JavaScript puede:
- Detectar elementos tan pronto como aparecen en el DOM
- Interactuar con elementos que Selenium considera "no interactuables"
- Ejecutarse de forma más confiable en SPAs (Single Page Applications)

#### 2. Múltiples Selectores Fallback

**Decisión**: Implementar una lista de selectores CSS ordenados por prioridad para cada elemento crítico.

**Razón**: LinkedIn puede cambiar sus selectores CSS sin aviso. Usar múltiples selectores aumenta la robustez:
```python
MODAL_SELECTORS = [
    'div[data-test-modal-id="easy-apply-modal"]',  # Más específico
    'div[data-test-modal-container]',
    'div.jobs-easy-apply-modal',
    'div[role="dialog"]'  # Más genérico
]
```

#### 3. Sistema de Confianza con Umbrales Configurables

**Decisión**: Implementar tres niveles de confianza (alta ≥0.85, media 0.65-0.85, baja <0.65) con umbrales configurables.

**Razón**: 
- Permite balance entre automatización y precisión
- Evita respuestas incorrectas que puedan perjudicar el perfil
- Configurable vía variables de entorno para ajustar según experiencia

#### 4. Estado Persistente para Recuperación

**Decisión**: Mantener archivo JSON con estado de trabajos procesados.

**Razón**:
- Evita duplicar postulaciones si el proceso se interrumpe
- Permite reanudar desde donde se quedó
- Facilita debugging al tener historial de acciones

## Components and Interfaces

### 1. ModalDetector

Responsable de detectar y esperar el modal de postulación.

```python
class ModalDetector:
    """Detecta el modal de postulación usando JavaScript y múltiples selectores."""
    
    MODAL_SELECTORS = [
        'div[data-test-modal-id="easy-apply-modal"]',
        'div[data-test-modal-container]',
        'div.jobs-easy-apply-modal',
        'div[role="dialog"]'
    ]
    
    def wait_for_modal(self, driver, timeout: int = 15) -> Optional[WebElement]:
        """
        Espera a que el modal aparezca usando JavaScript.
        
        Args:
            driver: Selenium WebDriver instance
            timeout: Tiempo máximo de espera en segundos
            
        Returns:
            WebElement del modal si se encuentra, None si timeout
        """
        pass
    
    def is_modal_visible(self, driver) -> bool:
        """Verifica si el modal está visible usando JavaScript."""
        pass
```

### 2. FormFieldDetector

Identifica y clasifica campos del formulario dentro del modal.

```python
class FormFieldDetector:
    """Detecta y clasifica campos del formulario de postulación."""
    
    FIELD_TYPES = {
        'text': 'input[data-test-single-line-text-form-component]',
        'email': 'select[id*="email"]',
        'phone_country': 'select[id*="phoneNumber-country"]',
        'phone_number': 'input[id*="phoneNumber-nationalNumber"]',
        'dropdown': 'select[data-test-text-entity-list-form-select]',
        'textarea': 'textarea',
        'radio': 'input[type="radio"]',
        'checkbox': 'input[type="checkbox"]',
        'file': 'input[type="file"]'
    }
    
    def detect_fields(self, modal_element) -> List[FormField]:
        """
        Detecta todos los campos dentro del modal.
        
        Args:
            modal_element: WebElement del modal
            
        Returns:
            Lista de FormField con tipo, label, y elemento
        """
        pass
    
    def get_field_purpose(self, field_element) -> str:
        """
        Identifica el propósito del campo usando label, placeholder, aria-label.
        
        Returns:
            String describiendo el propósito (ej: "years of experience")
        """
        pass
```

### 3. CVSelector

Selecciona el CV apropiado usando IA.

```python
class CVSelector:
    """Selecciona el CV apropiado basándose en el trabajo usando IA."""
    
    CV_MAPPING = {
        ('software', 'en'): 'CV Software Engineer Anabalon.pdf',
        ('software', 'es'): 'CV Software Engineer Anabalon.pdf',  # Mismo CV
        ('engineer', 'en'): 'CV Automatización_Data Anabalón.pdf',
        ('engineer', 'es'): 'CV Automatización_Data Anabalón.pdf'
    }
    
    def select_cv(self, job_title: str, job_description: str) -> CVRecommendation:
        """
        Selecciona el CV apropiado usando OpenRouter.
        
        Args:
            job_title: Título del trabajo
            job_description: Descripción completa del trabajo
            
        Returns:
            CVRecommendation con cv_type, language, confidence, reasoning
        """
        pass
    
    def detect_language(self, text: str) -> str:
        """Detecta el idioma del texto (en/es)."""
        pass
```

### 4. QuestionHandler

Responde preguntas del formulario usando IA.

```python
class QuestionHandler:
    """Responde preguntas del formulario usando IA y contexto del CV."""
    
    def answer_question(
        self, 
        question: str, 
        field_type: str,
        cv_context: str,
        available_options: Optional[List[str]] = None
    ) -> QuestionAnswer:
        """
        Responde una pregunta del formulario.
        
        Args:
            question: Texto de la pregunta
            field_type: Tipo de campo (text, number, dropdown, etc)
            cv_context: Contexto del CV seleccionado
            available_options: Opciones disponibles para dropdowns
            
        Returns:
            QuestionAnswer con answer, confidence, reasoning, sources
        """
        pass
    
    def handle_special_questions(self, question: str, field_type: str) -> Optional[QuestionAnswer]:
        """
        Maneja preguntas especiales comunes con respuestas predefinidas.
        
        Preguntas especiales:
        - Años de experiencia
        - Elegibilidad legal
        - Sponsorship
        - Salario
        
        Returns:
            QuestionAnswer si es pregunta especial, None si no
        """
        pass
```

### 5. ConfidenceSystem

Evalúa la confianza y decide si auto-submit.

```python
class ConfidenceSystem:
    """Sistema de confianza para decidir auto-submit vs manual review."""
    
    def __init__(self, high_threshold: float = 0.85, low_threshold: float = 0.65):
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
    
    def evaluate_application(self, answers: List[QuestionAnswer]) -> ApplicationDecision:
        """
        Evalúa todas las respuestas y decide la acción.
        
        Args:
            answers: Lista de respuestas con sus niveles de confianza
            
        Returns:
            ApplicationDecision con action (SUBMIT, UNCERTAIN, MANUAL) y reasoning
        """
        pass
    
    def calculate_overall_confidence(self, answers: List[QuestionAnswer]) -> float:
        """Calcula confianza general como promedio ponderado."""
        pass
```

### 6. StateManager

Maneja persistencia de estado para recuperación.

```python
class StateManager:
    """Maneja el estado de postulaciones para recuperación."""
    
    STATE_FILE = 'data/logs/application_state.json'
    
    def load_state(self) -> Dict[str, ProcessedJob]:
        """Carga el estado previo desde archivo."""
        pass
    
    def save_job_state(self, job_url: str, status: str, timestamp: datetime):
        """Guarda el estado de un trabajo procesado."""
        pass
    
    def is_job_processed(self, job_url: str) -> bool:
        """Verifica si un trabajo ya fue procesado."""
        pass
    
    def cleanup_old_entries(self, days: int = 30):
        """Elimina entradas más antiguas que N días."""
        pass
```

### 7. GoogleSheetsUpdater

Actualiza Google Sheets con resultados.

```python
class GoogleSheetsUpdater:
    """Actualiza Google Sheets con resultados de postulaciones."""
    
    def update_application(
        self,
        job_id: str,
        status: str,  # APPLIED, MANUAL, NO_DISPONIBLE, ERROR, INSEGURO
        cv_used: str,
        notes: str = ""
    ):
        """Actualiza una fila en Google Sheets con el resultado."""
        pass
    
    def add_confidence_notes(self, job_id: str, low_confidence_questions: List[str]):
        """Agrega notas sobre preguntas con baja confianza."""
        pass
```

### 8. TelegramNotifier

Envía notificaciones consolidadas.

```python
class TelegramNotifier:
    """Envía notificaciones consolidadas a Telegram."""
    
    def accumulate_result(self, job: Dict, status: str, details: Dict):
        """Acumula resultado de una postulación."""
        pass
    
    def send_summary(self):
        """
        Envía resumen consolidado al final del proceso.
        
        Incluye:
        - Total procesados, exitosos, manuales, no disponibles, errores
        - Estadísticas de IA: preguntas respondidas, tasa de automatización
        - Lista de trabajos que requieren atención manual
        """
        pass
```

## Data Models

### FormField

```python
@dataclass
class FormField:
    """Representa un campo del formulario."""
    element: WebElement
    field_type: str  # text, email, phone, dropdown, textarea, radio, checkbox, file
    label: str
    purpose: str  # Descripción del propósito del campo
    required: bool
    options: Optional[List[str]] = None  # Para dropdowns
```

### CVRecommendation

```python
@dataclass
class CVRecommendation:
    """Recomendación de CV por la IA."""
    cv_type: str  # 'software' o 'engineer'
    language: str  # 'en' o 'es'
    cv_path: str  # Ruta completa al archivo PDF
    confidence: float  # 0.0 a 1.0
    reasoning: str  # Explicación de la decisión
```

### QuestionAnswer

```python
@dataclass
class QuestionAnswer:
    """Respuesta a una pregunta del formulario."""
    question: str
    answer: str
    confidence: float  # 0.0 a 1.0
    reasoning: str
    sources: List[str]  # Partes del CV usadas para responder
    field_type: str
```

### ApplicationDecision

```python
@dataclass
class ApplicationDecision:
    """Decisión sobre cómo proceder con la postulación."""
    action: str  # SUBMIT, UNCERTAIN, MANUAL
    overall_confidence: float
    reasoning: str
    low_confidence_questions: List[str]  # Preguntas con confianza < threshold
```

### ProcessedJob

```python
@dataclass
class ProcessedJob:
    """Estado de un trabajo procesado."""
    url: str
    status: str  # APPLIED, MANUAL, NO_DISPONIBLE, ERROR, INSEGURO
    timestamp: datetime
    cv_used: Optional[str] = None
    error_message: Optional[str] = None
```

### ApplicationResult

```python
@dataclass
class ApplicationResult:
    """Resultado de una postulación."""
    job_url: str
    job_title: str
    company: str
    status: str  # APPLIED, MANUAL, NO_DISPONIBLE, ERROR, INSEGURO
    cv_used: Optional[str]
    questions_answered: int
    average_confidence: float
    notes: str
    timestamp: datetime
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, I identified several areas where properties can be consolidated to avoid redundancy:

1. **Job availability detection (1.1, 1.2)**: Combined into one property about detecting closure indicators
2. **Language detection and CV selection (6.1, 6.2, 6.3, 6.5)**: Combined into one property about language-based CV mapping
3. **Confidence thresholds (8.2, 8.3, 8.4)**: Combined into one property about confidence-based decision making
4. **Google Sheets updates (10.1, 10.2, 10.3)**: Combined into one property about complete record updates
5. **Conditional notes (10.4, 10.5)**: Combined into one property about status-based notes
6. **Notification content (11.3, 11.4, 11.5)**: Combined into one property about complete notification content
7. **Validation checks (14.1, 14.2)**: Combined into one property about pre-submission validation
8. **State structure (15.1, 15.3)**: Combined into one property about state file format

### Property 1: Job Availability Detection

*For any* job page containing closure indicators (texts like "No longer accepting applications", "Ya no se aceptan solicitudes", "This job is no longer available", "Closed"), the system should mark the job as "NO_DISPONIBLE" in Google Sheets and skip the application process.

**Validates: Requirements 1.1, 1.2, 1.4**

### Property 2: Unavailable Job Updates

*For any* job marked as "NO_DISPONIBLE", the Google Sheets record should have Estado field set to "No disponible" and include an explanatory note.

**Validates: Requirements 1.3**

### Property 3: Description Expansion Detection

*For any* job page, if an expansion button exists (with texts "Ver más", "Show more", "See more"), the system should click it and extract the full expanded description.

**Validates: Requirements 2.1, 2.2, 2.4**

### Property 4: Full Description to AI

*For any* job being classified, the complete description (after expansion if applicable) should be passed to the AI classifier.

**Validates: Requirements 2.5**

### Property 5: Modal Detection with Fallback Selectors

*For any* application modal, at least one of the fallback selectors (div[data-test-modal-id="easy-apply-modal"], div[data-test-modal-container], div.jobs-easy-apply-modal, div[role="dialog"]) should successfully detect the modal when it appears.

**Validates: Requirements 3.2**

### Property 6: Form Field Scoping

*For any* form field search, only elements within the modal context should be detected, ignoring elements outside the modal (like LinkedIn's language dropdown).

**Validates: Requirements 3.3, 4.4**

### Property 7: JavaScript Fallback for Field Filling

*For any* form field that Selenium fails to fill, the system should attempt to fill it using JavaScript as a fallback method.

**Validates: Requirements 3.4**

### Property 8: Field Type Detection

*For any* form within the application modal, the system should correctly detect and classify all field types (text input, email, phone, dropdown, textarea, radio, checkbox, file upload).

**Validates: Requirements 4.1**

### Property 9: Field Purpose Identification

*For any* detected form field, the system should identify its purpose using available metadata (label, placeholder, aria-label, or id).

**Validates: Requirements 4.3**

### Property 10: Field Detection Logging

*For any* detected form field, the system should log both its type and identified purpose.

**Validates: Requirements 4.5**

### Property 11: CV Recommendation Format

*For any* job analyzed by the AI classifier, the CV recommendation should contain a valid cv_type ("software" or "engineer"), a confidence value between 0.0 and 1.0, and reasoning.

**Validates: Requirements 5.3, 5.4**

### Property 12: CV Usage Recording

*For any* application submitted, the CV file used should be recorded in the Google Sheets "CV_Usado" field.

**Validates: Requirements 5.6**

### Property 13: Language-Based CV Selection

*For any* job posting, the system should select the CV version matching both the job type (software/engineer) and detected language (en/es) according to the CV mapping.

**Validates: Requirements 6.1, 6.2, 6.3, 6.5**

### Property 14: Question Extraction

*For any* question in the application form, the system should extract both the question text and the field type.

**Validates: Requirements 7.1**

### Property 15: Question Context to AI

*For any* question sent to the AI, both the question text and the selected CV context should be included in the request.

**Validates: Requirements 7.2**

### Property 16: AI Response Format

*For any* question answered by the AI, the response should be valid JSON containing all required fields: answer, confidence, reasoning, and sources.

**Validates: Requirements 7.4**

### Property 17: Answer Format Validation

*For any* AI-generated answer, the format should match the field type requirements (e.g., numbers for numeric fields, valid options for dropdowns).

**Validates: Requirements 7.5**

### Property 18: Question-Answer Logging

*For any* question answered by the system, both the question and answer should be logged.

**Validates: Requirements 7.6**

### Property 19: Confidence Value Range

*For any* AI response, the confidence value should be between 0.0 and 1.0 inclusive.

**Validates: Requirements 8.1**

### Property 20: Confidence-Based Decision Making

*For any* application with AI-generated answers, the system should: auto-submit if all confidences ≥ 0.85, mark as "INSEGURO" if any confidence is between 0.65-0.85, or mark as "MANUAL" if any confidence < 0.65.

**Validates: Requirements 8.2, 8.3, 8.4**

### Property 21: Uncertain Application Notes

*For any* application marked as "INSEGURO", the Google Sheets notes should list which questions had confidence below the high threshold.

**Validates: Requirements 8.5**

### Property 22: Experience Question Format

*For any* question about years of experience with a numeric field, the AI response should be an integer without units.

**Validates: Requirements 9.1**

### Property 23: Legal Eligibility Response

*For any* question about legal eligibility to work, the AI should respond with "Yes" or "Sí" with confidence ≥ 0.95.

**Validates: Requirements 9.2**

### Property 24: Sponsorship Response

*For any* question about visa sponsorship requirements, the AI should respond with "No" with confidence ≥ 0.95.

**Validates: Requirements 9.3**

### Property 25: Salary Question Configuration

*For any* question about salary expectations, the AI should use the response configured in respuestas_comunes.json.

**Validates: Requirements 9.4**

### Property 26: Numeric Answer Validation

*For any* question with a numeric field type, the AI response should be validated as a valid number before being returned.

**Validates: Requirements 9.5**

### Property 27: Google Sheets Complete Update

*For any* completed application (successful or failed), the Google Sheets record should be immediately updated with all required fields: ID, fecha_aplicación, Empresa, Puesto, URL, Ubicación, tipo_aplicación, CV_Usado, Estado, Último_Update, Notas.

**Validates: Requirements 10.1, 10.2**

### Property 28: Status Value Validation

*For any* Google Sheets update, the Estado field should contain exactly one of: "APPLIED", "MANUAL", "NO_DISPONIBLE", "ERROR", "INSEGURO".

**Validates: Requirements 10.3**

### Property 29: Status-Based Notes

*For any* application with Estado "INSEGURO", the Notas field should include low-confidence questions; for Estado "ERROR", the Notas field should include the error message.

**Validates: Requirements 10.4, 10.5**

### Property 30: Google Sheets Error Resilience

*For any* Google Sheets API error, the system should continue processing remaining applications without terminating.

**Validates: Requirements 10.6**

### Property 31: Result Accumulation

*For any* batch of applications processed, all results should be accumulated during execution for the final summary.

**Validates: Requirements 11.1**

### Property 32: Single Consolidated Notification

*For any* complete execution run, exactly one Telegram notification should be sent at the end, regardless of the number of applications processed.

**Validates: Requirements 11.2**

### Property 33: Complete Notification Content

*For any* Telegram notification sent, it should include: total jobs processed, counts by status (successful, manual, unavailable, errors), AI statistics (questions answered, automation rate, average confidence), and list of jobs requiring manual attention.

**Validates: Requirements 11.3, 11.4, 11.5**

### Property 34: Telegram Optional

*For any* execution, if Telegram is not configured, the system should complete successfully without sending notifications.

**Validates: Requirements 11.6**

### Property 35: Random Delays Between Applications

*For any* two consecutive applications, the delay between them should be randomly selected from the range 8-15 seconds.

**Validates: Requirements 12.1**

### Property 36: Session Cookie Persistence

*For any* execution, the system should load and use saved cookies to maintain the LinkedIn session.

**Validates: Requirements 12.3**

### Property 37: Comprehensive Action Logging

*For any* execution, the logs should contain entries for all major actions: page loads, modal detection, fields found, AI responses.

**Validates: Requirements 13.1**

### Property 38: Screenshot on Field Fill Failure

*For any* form field that cannot be filled, a screenshot should be saved to data/logs/debug_*.png.

**Validates: Requirements 13.2**

### Property 39: HTML Capture on Modal Detection Failure

*For any* application where the modal is not detected, the page HTML should be saved to data/logs/debug_html_*.html.

**Validates: Requirements 13.3**

### Property 40: Structured Log Format

*For any* log entry, it should include a timestamp and severity level (INFO, WARNING, ERROR).

**Validates: Requirements 13.4**

### Property 41: Log Rotation

*For any* log file exceeding 10MB, the system should automatically rotate to a new log file.

**Validates: Requirements 13.5**

### Property 42: Pre-Submission Validation

*For any* application ready to submit, the system should validate that all required fields are filled and that formats are correct (emails contain @, phones are numeric, URLs are valid).

**Validates: Requirements 14.1, 14.2**

### Property 43: Invalid Option Confidence Reduction

*For any* single-choice answer that doesn't match available options, the confidence should be reduced by 20% and re-evaluated.

**Validates: Requirements 14.3**

### Property 44: Critical Field Validation Failure

*For any* application with validation failures in critical fields (email, phone), the status should be set to "MANUAL" instead of submitting.

**Validates: Requirements 14.4**

### Property 45: Validation Failure Logging

*For any* validation failure, the specific failure should be logged.

**Validates: Requirements 14.5**

### Property 46: State File Persistence

*For any* execution, the system should maintain a state file at data/logs/application_state.json containing URL, timestamp, and result for each processed job.

**Validates: Requirements 15.1, 15.3**

### Property 47: State-Based Job Filtering

*For any* execution start, the system should load the previous state and skip jobs that were already processed.

**Validates: Requirements 15.2**

### Property 48: Resumption After Interruption

*For any* interrupted execution, the next execution should resume from the first unprocessed job based on the state file.

**Validates: Requirements 15.4**

### Property 49: State Cleanup

*For any* state file, entries older than 30 days should be automatically removed.

**Validates: Requirements 15.5**

## Error Handling

### Error Categories

1. **Network Errors**
   - LinkedIn page load failures
   - OpenRouter API timeouts
   - Google Sheets API failures
   - Telegram API failures

2. **Detection Errors**
   - Modal not appearing
   - Form fields not found
   - Expansion button not found

3. **Validation Errors**
   - Invalid AI responses
   - Format validation failures
   - Missing required fields

4. **Anti-Bot Errors**
   - CAPTCHA detection
   - Session blocks
   - Rate limiting

### Error Handling Strategies

#### Network Errors

**OpenRouter API Errors**:
- Implement exponential backoff for rate limit errors (429)
- Retry up to 3 times with delays: 2s, 4s, 8s
- If all retries fail, mark job as "MANUAL"
- Log the error with full context

**Google Sheets API Errors**:
- Catch exceptions and log them
- Continue processing remaining jobs
- Accumulate failed updates and retry at the end
- If final retry fails, log warning but don't fail the entire run

**Telegram API Errors**:
- Catch exceptions silently
- Log the error
- Continue execution (notifications are non-critical)

#### Detection Errors

**Modal Not Appearing**:
- Wait up to 15 seconds using JavaScript polling
- Try all fallback selectors in order
- If all fail, save page HTML for debugging
- Mark job as "MANUAL"
- Continue with next job

**Form Fields Not Found**:
- Log warning with available HTML structure
- Save screenshot for debugging
- Mark job as "MANUAL"
- Continue with next job

#### Validation Errors

**Invalid AI Response Format**:
- Log the invalid response
- Retry the AI call once
- If retry fails, mark job as "MANUAL"
- Continue with next job

**Format Validation Failures**:
- Log the validation error
- For critical fields (email, phone): mark as "MANUAL"
- For non-critical fields: use best effort or skip field
- Continue with application if possible

#### Anti-Bot Errors

**CAPTCHA Detection**:
- Detect CAPTCHA by looking for specific elements
- Immediately pause execution
- Mark all remaining jobs as "MANUAL"
- Save state and exit gracefully
- Log clear message for user intervention

**Session Block**:
- Detect by checking for login redirect
- Save state immediately
- Mark remaining jobs as "MANUAL"
- Exit gracefully with clear error message

### Error Recovery

All errors should:
1. Be logged with full context (timestamp, job URL, error message, stack trace)
2. Save debugging artifacts (screenshots, HTML dumps)
3. Update Google Sheets with error status and notes
4. Not crash the entire process (graceful degradation)
5. Allow resumption in next execution via state file

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests for comprehensive coverage:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property-based tests**: Verify universal properties across randomized inputs

### Unit Testing

Unit tests should focus on:

1. **Specific Examples**
   - Modal detection with known HTML structure
   - CV selection for specific job titles
   - Special question handling (eligibility, sponsorship)
   - State file loading and saving

2. **Edge Cases**
   - Empty job descriptions
   - Missing form fields
   - Malformed AI responses
   - Network timeouts

3. **Error Conditions**
   - CAPTCHA detection
   - Session blocks
   - API failures
   - Invalid configurations

4. **Integration Points**
   - OpenRouter API integration
   - Google Sheets API integration
   - Telegram API integration
   - Selenium WebDriver interaction

### Property-Based Testing

Property-based tests should use **Hypothesis** (Python's PBT library) with minimum 100 iterations per test.

Each property test must:
- Reference its design document property in a comment
- Use appropriate generators for test data
- Verify the universal property holds for all generated inputs

#### Test Configuration

```python
from hypothesis import given, settings
import hypothesis.strategies as st

# Configure for minimum 100 iterations
@settings(max_examples=100)
@given(...)
def test_property_name(...):
    """
    Feature: linkedin-auto-applier-mejoras, Property X: [property text]
    """
    pass
```

#### Key Property Tests

1. **Modal Detection (Property 5)**
   - Generate HTML with modal using different selectors
   - Verify at least one selector finds the modal

2. **Field Scoping (Property 6)**
   - Generate HTML with fields inside and outside modal
   - Verify only modal fields are detected

3. **CV Selection (Property 13)**
   - Generate random job titles and descriptions in different languages
   - Verify correct CV is selected based on language and type

4. **Confidence-Based Decisions (Property 20)**
   - Generate random confidence values
   - Verify correct action (SUBMIT/UNCERTAIN/MANUAL) is taken

5. **Format Validation (Property 42)**
   - Generate random form data with valid and invalid formats
   - Verify validation catches all format errors

6. **State Persistence (Property 47)**
   - Generate random job lists and process states
   - Verify processed jobs are correctly filtered

#### Generators

```python
# Job data generator
@st.composite
def job_data(draw):
    return {
        'url': draw(st.text(min_size=10)),
        'title': draw(st.text(min_size=5)),
        'description': draw(st.text(min_size=20)),
        'company': draw(st.text(min_size=3))
    }

# Confidence value generator
confidence_values = st.floats(min_value=0.0, max_value=1.0)

# Form field generator
@st.composite
def form_field(draw):
    field_types = ['text', 'email', 'phone', 'dropdown', 'textarea']
    return {
        'type': draw(st.sampled_from(field_types)),
        'label': draw(st.text(min_size=3)),
        'required': draw(st.booleans())
    }
```

### Test Coverage Goals

- **Unit test coverage**: Minimum 80% code coverage
- **Property test coverage**: All 49 correctness properties must have corresponding tests
- **Integration test coverage**: All external API integrations must be tested
- **Error path coverage**: All error handling paths must be tested

### Testing Anti-Bot Measures

Anti-bot measures (delays, human-like behavior) should NOT be tested in unit/property tests as they would slow down the test suite. Instead:

- Mock the delay functions in tests
- Test that delay functions are called with correct parameters
- Manually verify anti-bot behavior in staging environment

### Mocking Strategy

For external dependencies:
- **OpenRouter API**: Mock with predefined responses for different scenarios
- **Google Sheets API**: Mock with in-memory data structure
- **Telegram API**: Mock to verify message content without sending
- **Selenium WebDriver**: Use real WebDriver with local HTML files for integration tests

