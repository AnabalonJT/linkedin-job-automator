# 🏗️ Estructura Funcional del Proyecto - LinkedIn Job Automator

## 📋 Índice
1. [Visión General del Sistema](#visión-general-del-sistema)
2. [Módulos y Responsabilidades](#módulos-y-responsabilidades)
3. [Flujo de Ejecución Completo](#flujo-de-ejecución-completo)
4. [Dependencias entre Funciones](#dependencias-entre-funciones)
5. [Problemas Identificados](#problemas-identificados)
6. [Propuesta de Modularización](#propuesta-de-modularización)

---

## 1. Visión General del Sistema

### Arquitectura Actual
```
┌─────────────────────────────────────────────────────────────┐
│                    N8N (Orquestador)                        │
│              Trigger: Cron (09:00 AM diario)                │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Scraper    │ │   Applier    │ │   Sheets     │
│   (Buscar)   │ │  (Postular)  │ │   (Sync)     │
└──────────────┘ └──────────────┘ └──────────────┘
        │            │            │
        └────────────┼────────────┘
                     │
              ┌──────▼──────┐
              │  Telegram   │
              │ (Notificar) │
              └─────────────┘
```

### Componentes Principales

1. **linkedin_scraper.py** - Búsqueda de trabajos
2. **linkedin_applier.py** - Postulación automática
3. **ia_integration.py** - Integración de IA
4. **ia_classifier.py** - Clasificación y respuestas
5. **openrouter_client.py** - Cliente API OpenRouter
6. **cv_processor.py** - Procesamiento de CVs
7. **selenium_extractor.py** - Extracción de elementos del DOM
8. **google_sheets_manager.py** - Sincronización con Google Sheets
9. **telegram_notifier.py** - Notificaciones
10. **credentials_manager.py** - Gestión de credenciales
11. **utils.py** - Utilidades compartidas

---

## 2. Módulos y Responsabilidades

### 2.1 linkedin_scraper.py
**Responsabilidad**: Buscar trabajos en LinkedIn con Easy Apply

**Funciones Principales**:
- `setup_driver()` - Configura Selenium WebDriver
- `login(email, password)` - Inicia sesión en LinkedIn
- `search_jobs(keywords, location, num_jobs)` - Busca trabajos
- `extract_job_data(job_card)` - Extrae datos de una tarjeta
- `check_easy_apply_in_detail(job_card)` - Verifica Easy Apply y extrae descripción

**Dependencias**:
- Selenium WebDriver
- google_sheets_manager (para deduplicación)
- utils (Config, Logger)

**Problemas Actuales**:
- ❌ No puede expandir "mostrar más" en descripciones
- ⚠️ Descripciones incompletas (solo primeros 200-500 chars)


### 2.2 linkedin_applier.py
**Responsabilidad**: Aplicar automáticamente a trabajos con Easy Apply

**Clase Principal**: `LinkedInApplier`

**Funciones Principales**:

#### Función de Entrada
- `apply_to_job(job)` - Orquesta toda la aplicación a un trabajo
  - Carga la página del trabajo
  - Extrae descripción completa
  - Clasifica con IA (o usa keywords)
  - Abre modal Easy Apply
  - Procesa formulario multi-paso

#### Procesamiento de Formulario
- `process_application_form(job, result)` - Loop principal de formulario
  - Itera hasta 10 pasos máximo
  - Llama a `fill_current_form_step()` en cada paso
  - Busca botón "Siguiente/Revisar/Enviar"
  - Detecta loops infinitos

- `fill_current_form_step(job, result, seen_questions)` - Rellena paso actual
  - Llama a handlers específicos por tipo de campo
  - Trackea preguntas vistas (evita duplicados)
  - Retorna lista de preguntas sin respuesta

#### Handlers por Tipo de Campo
- `handle_cv_upload(job, result)` - Sube CV apropiado
- `handle_text_question(text_input, result, seen_questions, new_questions)` - Preguntas de texto
- `handle_open_question(textarea, result, seen_questions, new_questions)` - Preguntas abiertas
- `handle_radio_questions(result, seen_questions, new_questions)` - Radio buttons
- `handle_dropdown_questions(result, seen_questions, new_questions)` - Dropdowns/selects

#### Funciones Auxiliares
- `fill_text_field(field, result)` - Rellena campos genéricos (email, teléfono)
- `fill_textarea(textarea, result)` - Rellena textareas genéricos
- `detect_input_type(text_input)` - Detecta tipo esperado (number, date, text)
- `find_answer_for_question(question_text)` - Busca en respuestas_comunes.json

**Dependencias**:
- ia_integration (clasificación y respuestas)
- utils (Config, Logger, select_cv_by_keywords)
- Selenium WebDriver

**Problemas Actuales**:
- ❌ No detecta correctamente el botón "Solicitud sencilla" (Easy Apply)
- ❌ No reconoce cuando el modal se abre vs cuando no
- ❌ No encuentra botón "Siguiente/Revisar" después de rellenar
- ⚠️ Mezcla preguntas de texto con dropdowns (solo responde uno u otro)
- ⚠️ No aplica threshold de confianza 0.7 para marcar como MANUAL
- ⚠️ Lógica de cv_by_keywords parece redundante con clasificación IA


### 2.3 ia_integration.py
**Responsabilidad**: Interfaz unificada para todos los componentes de IA

**Clase Principal**: `IAIntegration`

**Funciones Principales**:
- `__init__(logger, debug)` - Inicializa todos los módulos IA
  - Carga CVProcessor
  - Inicializa AIClassifier
  - Inicializa SeleniumExtractor
- `classify_job(title, description, requirements)` - Clasifica trabajo y recomienda CV
- `set_cv_type(cv_type)` - Cambia CV activo para respuestas
- `answer_question(question_text, question_type, options, previous_answers)` - Responde pregunta
- `get_stats()` - Obtiene estadísticas de uso
- `format_stats_for_telegram()` - Formatea stats para notificación

**Dependencias**:
- openrouter_client
- cv_processor
- ia_classifier
- selenium_extractor

**Problemas Actuales**:
- ⚠️ Parece que `ia_integration.py` y `ia_classifier.py` tienen funciones duplicadas
- ⚠️ No está claro cuándo usar uno vs el otro
- ✅ Funciona bien como interfaz unificada

### 2.4 ia_classifier.py
**Responsabilidad**: Lógica de clasificación y respuestas con confianza

**Clase Principal**: `AIClassifier`

**Funciones Principales**:
- `classify_job(title, description, requirements, url)` - Clasifica trabajo
  - Retorna: job_type, match_percentage, confidence, recommended_cv, reasoning
- `answer_question(question_text, question_type, options, previous_answers)` - Responde pregunta
  - Retorna: answer, confidence, reasoning, sources, auto_submit
- `set_cv_type(cv_type)` - Cambia CV activo
- `get_current_cv_context()` - Obtiene contexto CV actual
- `get_stats()` - Estadísticas de uso
- `extract_best_option(options, question_text)` - Selecciona mejor opción de múltiple choice
- `evaluate_answer_quality(question, answer)` - Evalúa calidad de respuesta

**Dependencias**:
- openrouter_client
- cv_processor

**Problemas Actuales**:
- ⚠️ Duplica funcionalidad con ia_integration
- ✅ Tiene lógica de confianza bien implementada


### 2.5 openrouter_client.py
**Responsabilidad**: Comunicación con API de OpenRouter (Llama 3.3 70B)

**Clase Principal**: `OpenRouterClient`

**Funciones Principales**:
- `call(message, system_prompt, temperature, max_tokens, expect_json)` - Llamada genérica a API
- `classify_job(title, description, requirements, cv_context)` - Clasificación de trabajo
- `answer_question(question_text, question_type, options, cv_context, previous_answers)` - Respuesta a pregunta
- `extract_json_response(response)` - Parsea respuesta JSON

**Dependencias**:
- requests (HTTP)
- OPENROUTER_API_KEY (env)

**Problemas Actuales**:
- ✅ Funciona correctamente
- ⚠️ No tiene retry logic para errores de red

### 2.6 cv_processor.py
**Responsabilidad**: Extracción y gestión de contexto de CVs

**Clase Principal**: `CVProcessor`

**Funciones Principales**:
- `load_or_create()` - Carga o crea contexto CV unificado
- `extract_pdf_to_json(pdf_path)` - Extrae datos de PDF
- `get_context_as_string(context_obj)` - Convierte a string para IA
- `get_context_by_type(cv_type)` - Obtiene contexto por tipo (deprecated)

**Dependencias**:
- PyPDF2 o pdfplumber (extracción PDF)

**Problemas Actuales**:
- ⚠️ Contexto muy corto (~2453 chars, ideal sería 2000-3000+)
- ⚠️ No está extrayendo toda la información del CV
- ✅ Sistema unificado funciona bien

### 2.7 selenium_extractor.py
**Responsabilidad**: Extracción de elementos del formulario

**Clase Principal**: `SeleniumExtractor`

**Funciones Principales**:
- `extract_current_question()` - Extrae pregunta actual del formulario
- `_find_question_element()` - Localiza elemento de pregunta
- `_extract_question_text(element)` - Extrae texto de pregunta
- `_detect_question_type(element)` - Detecta tipo (text, radio, dropdown, etc.)
- `_extract_options(element)` - Extrae opciones disponibles
- `fill_question_answer(answer, question_type)` - Rellena respuesta
- `proceed_to_next()` - Click en botón Next
- `submit_application()` - Click en botón Submit

**Dependencias**:
- Selenium WebDriver

**Problemas Actuales**:
- ❌ NO se está usando en linkedin_applier.py
- ⚠️ Tiene lógica duplicada con los handlers de linkedin_applier
- ⚠️ Parece ser un módulo abandonado o en desarrollo


---

## 3. Flujo de Ejecución Completo

### 3.1 Flujo de Scraping (linkedin_scraper.py)
```
1. setup_driver()
   └─> Configura Chrome con undetected_chromedriver
   
2. login(email, password)
   ├─> load_cookies() - Intenta usar cookies guardadas
   ├─> Si falla: Login manual
   └─> save_cookies() - Guarda sesión

3. search_jobs(keywords, location, num_jobs, existing_job_ids)
   ├─> Construye URL de búsqueda con filtros
   ├─> Itera por lotes de 5 trabajos
   ├─> Para cada tarjeta:
   │   ├─> extract_job_data(job_card)
   │   │   ├─> Extrae título, empresa, ubicación, URL
   │   │   └─> check_easy_apply_in_detail(job_card)
   │   │       ├─> Click en tarjeta
   │   │       ├─> Extrae descripción completa
   │   │       └─> Verifica botón "Solicitud sencilla"
   │   └─> Deduplica contra existing_job_ids
   └─> Retorna lista de trabajos nuevos

4. Guarda en jobs_found.json con flag is_new: true
```

### 3.2 Flujo de Aplicación (linkedin_applier.py)
```
1. apply_to_job(job)
   ├─> Navega a job['url']
   ├─> Extrae descripción completa (con botón "mostrar más")
   │
   ├─> CLASIFICACIÓN
   │   ├─> select_cv_by_keywords(title, description) - Prioridad 1
   │   └─> ia.classify_job(title, description, requirements) - Solo para stats
   │
   ├─> ABRIR MODAL EASY APPLY
   │   ├─> Busca botón con múltiples selectores
   │   ├─> Intenta click normal
   │   ├─> Si falla: JavaScript click
   │   └─> Verifica que modal está visible (CRÍTICO)
   │
   └─> process_application_form(job, result)
       └─> Loop hasta 10 pasos:
           ├─> fill_current_form_step(job, result, seen_questions)
           │   ├─> handle_cv_upload()
           │   ├─> handle_text_question() - Para cada input[type="text"]
           │   ├─> handle_open_question() - Para cada textarea
           │   ├─> handle_radio_questions() - Para todos los radio groups
           │   └─> handle_dropdown_questions() - Para todos los selects
           │
           ├─> Busca botón "Siguiente/Revisar/Enviar"
           ├─> Click en botón
           └─> Si es "Enviar": return True (éxito)
```


### 3.3 Flujo de Respuesta a Preguntas (con IA)
```
handle_text_question(text_input, result, seen_questions, new_questions)
├─> Extrae texto de pregunta (label, placeholder, aria-label)
├─> Verifica si ya fue vista (seen_questions)
├─> detect_input_type(text_input) - Detecta si espera number, date, text
│
├─> SI IA HABILITADA:
│   ├─> ia.answer_question(question_text, question_type, options, previous_answers)
│   │   └─> ia_classifier.answer_question()
│   │       └─> openrouter_client.answer_question()
│   │           └─> API Call a Llama 3.3 70B
│   │               └─> Retorna: {answer, confidence, reasoning, sources, auto_submit}
│   │
│   ├─> VALIDACIÓN:
│   │   ├─> Si "información no disponible": low_confidence_count++
│   │   ├─> Si low_confidence_count >= 3: ABORTAR (status = MANUAL)
│   │   └─> Si pregunta de años: Convertir a número entero
│   │
│   └─> Si confidence >= 0.85: Rellenar campo
│
├─> SI NO IA O FALLA:
│   └─> find_answer_for_question(question_text)
│       └─> Busca en respuestas_comunes.json por patrones regex
│
└─> Guarda en result['answers_log'][question_text]
```

### 3.4 Flujo de Clasificación de Trabajo
```
ia.classify_job(title, description, requirements)
└─> ia_classifier.classify_job()
    └─> openrouter_client.classify_job(title, description, requirements, cv_context)
        └─> API Call con prompt:
            "Clasifica este trabajo según el CV del candidato"
            
        └─> Retorna:
            {
              job_type: "software|consultoria|otro",
              match_percentage: 0-100,
              confidence: 0.0-1.0,
              recommended_cv: "software|engineer",
              reasoning: "...",
              top_matching_skills: [...],
              missing_skills: [...],
              auto_submit: boolean
            }
```

---

## 4. Dependencias entre Funciones

### 4.1 Mapa de Dependencias
```
linkedin_applier.py
├─> apply_to_job()
    ├─> select_cv_by_keywords() [utils.py]
    ├─> ia.classify_job() [ia_integration.py]
    │   └─> ia_classifier.classify_job() [ia_classifier.py]
    │       └─> openrouter_client.classify_job() [openrouter_client.py]
    │
    └─> process_application_form()
        └─> fill_current_form_step()
            ├─> handle_cv_upload()
            │   └─> select_cv_by_keywords() [utils.py]
            │
            ├─> handle_text_question()
            │   ├─> detect_input_type()
            │   ├─> ia.answer_question() [ia_integration.py]
            │   │   └─> ia_classifier.answer_question() [ia_classifier.py]
            │   │       └─> openrouter_client.answer_question() [openrouter_client.py]
            │   └─> find_answer_for_question()
            │
            ├─> handle_open_question()
            │   ├─> ia.answer_question()
            │   └─> find_answer_for_question()
            │
            ├─> handle_radio_questions()
            │   ├─> ia.answer_question()
            │   └─> find_answer_for_question()
            │
            └─> handle_dropdown_questions()
                ├─> ia.answer_question()
                └─> find_answer_for_question()
```


### 4.2 Funciones que Hablan con Cuáles

| Función Origen | Llama a | Propósito |
|----------------|---------|-----------|
| `apply_to_job()` | `select_cv_by_keywords()` | Seleccionar CV por keywords |
| `apply_to_job()` | `ia.classify_job()` | Clasificar trabajo (solo stats) |
| `apply_to_job()` | `process_application_form()` | Procesar formulario |
| `process_application_form()` | `fill_current_form_step()` | Rellenar paso actual |
| `fill_current_form_step()` | `handle_cv_upload()` | Subir CV |
| `fill_current_form_step()` | `handle_text_question()` | Responder input text |
| `fill_current_form_step()` | `handle_open_question()` | Responder textarea |
| `fill_current_form_step()` | `handle_radio_questions()` | Responder radio buttons |
| `fill_current_form_step()` | `handle_dropdown_questions()` | Responder dropdowns |
| `handle_text_question()` | `detect_input_type()` | Detectar tipo esperado |
| `handle_text_question()` | `ia.answer_question()` | Obtener respuesta IA |
| `handle_text_question()` | `find_answer_for_question()` | Buscar en config |
| `handle_open_question()` | `ia.answer_question()` | Obtener respuesta IA |
| `handle_open_question()` | `find_answer_for_question()` | Buscar en config |
| `handle_radio_questions()` | `ia.answer_question()` | Obtener respuesta IA |
| `handle_radio_questions()` | `find_answer_for_question()` | Buscar en config |
| `handle_dropdown_questions()` | `ia.answer_question()` | Obtener respuesta IA |
| `handle_dropdown_questions()` | `find_answer_for_question()` | Buscar en config |
| `ia.answer_question()` | `ia_classifier.answer_question()` | Delegación |
| `ia_classifier.answer_question()` | `openrouter_client.answer_question()` | API call |

---

## 5. Problemas Identificados

### 5.1 Problemas Críticos (Bloquean Postulaciones)

#### ❌ Problema 1: No encuentra botón "Siguiente/Revisar"
**Ubicación**: `process_application_form()` línea ~580

**Síntoma**: Después de rellenar el formulario, no encuentra el botón para avanzar
```
[WARNING]   ❌ No se encontró botón de acción
[INFO]   📊 Debug: Intentados estos selectores:
[INFO]       - aria-label=Revisar
[INFO]       - aria-label=Review
[INFO]       - aria-label=Enviar
```

**Causa Raíz**:
- Los selectores están buscando por `aria-label` exacto
- LinkedIn usa botones con clases dinámicas
- El botón puede estar fuera del viewport

**Solución Propuesta**:
```python
# Buscar botones dentro del modal específicamente
modal = driver.find_element(By.CSS_SELECTOR, "div[role='dialog']")
buttons = modal.find_elements(By.TAG_NAME, "button")

for button in buttons:
    text = button.text.lower()
    aria = (button.get_attribute('aria-label') or '').lower()
    
    if any(word in f"{text} {aria}" for word in ['siguiente', 'next', 'revisar', 'review', 'enviar', 'submit']):
        # Verificar que no sea "Volver" o "Back"
        if not any(word in f"{text} {aria}" for word in ['volver', 'back', 'cancel']):
            return button
```


#### ❌ Problema 2: No detecta correctamente si el modal se abrió
**Ubicación**: `apply_to_job()` línea ~240

**Síntoma**: Dice que el modal está abierto pero en realidad no lo está
```
[INFO]   ✓ Modal detectado - formulario listo
[INFO]   ✓ Formulario confirmado (2 campos encontrados)
```

**Causa Raíz**:
- Busca elementos en TODO el DOM, no solo dentro del modal
- El dropdown de idioma (es_ES) está en la página principal, no en el modal
- No verifica que el modal sea VISIBLE y esté en primer plano

**Solución Propuesta**:
```python
# Verificar que el modal está VISIBLE y en primer plano
try:
    modal = WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "div[role='dialog'].artdeco-modal--layer-default"))
    )
    
    # Verificar que tiene z-index alto (está en primer plano)
    z_index = modal.value_of_css_property('z-index')
    if int(z_index) < 1000:
        raise Exception("Modal no está en primer plano")
    
    # Buscar elementos DENTRO del modal
    form_elements = modal.find_elements(By.CSS_SELECTOR, "input, textarea, select")
    
    # Filtrar elementos que NO son del header del modal
    valid_elements = [el for el in form_elements if 'language' not in el.get_attribute('id')]
    
    if len(valid_elements) == 0:
        raise Exception("No hay campos de formulario en el modal")
        
except:
    logger.error("Modal no se abrió correctamente")
    return False
```

#### ❌ Problema 3: Mezcla preguntas de diferentes tipos
**Ubicación**: `fill_current_form_step()` línea ~620

**Síntoma**: Solo responde dropdowns O preguntas de texto, no ambos en el mismo paso

**Causa Raíz**:
- Los handlers se ejecutan secuencialmente
- Si `handle_text_question()` procesa un input, puede marcar la pregunta como vista
- Luego `handle_dropdown_questions()` no la procesa porque ya está en `seen_questions`

**Solución Propuesta**:
- Separar `seen_questions` por tipo de campo
- O mejor: Procesar TODOS los campos del formulario antes de buscar botón


### 5.2 Problemas Importantes (Afectan Calidad)

#### ⚠️ Problema 4: No aplica threshold de confianza 0.7
**Ubicación**: Múltiples handlers (handle_text_question, handle_radio_questions, etc.)

**Síntoma**: No marca preguntas como MANUAL cuando confianza < 0.7

**Causa Raíz**:
- El código verifica `confidence >= 0.85` para auto_submit
- Pero no hay lógica para marcar como MANUAL cuando `0.6 < confidence < 0.85`
- Solo cuenta respuestas "información no disponible"

**Solución Propuesta**:
```python
if ia_confidence < 0.7:
    # Marcar como MANUAL
    result['status'] = 'MANUAL'
    result['manual_reason'] = f'Low confidence ({ia_confidence:.2f}) on question: {question_text}'
    new_questions.append({
        'question': question_text,
        'ia_answer': ia_answer,
        'confidence': ia_confidence,
        'reason': 'Below 0.7 threshold'
    })
    return True  # No rellenar
```

#### ⚠️ Problema 5: cv_by_keywords parece redundante
**Ubicación**: `apply_to_job()` línea ~96

**Síntoma**: Usa `select_cv_by_keywords()` como prioridad 1, IA solo para stats

**Causa Raíz**:
- Hay dos sistemas de clasificación:
  1. `select_cv_by_keywords()` - Basado en keywords hardcodeadas
  2. `ia.classify_job()` - Basado en IA con contexto completo
- El código usa keywords como prioridad, IA solo para logging

**Pregunta**: ¿Es necesario mantener ambos? ¿O confiar solo en IA?

**Opciones**:
1. **Opción A**: Eliminar keywords, usar solo IA
2. **Opción B**: Usar keywords como fallback si IA falla
3. **Opción C**: Usar IA como prioridad, keywords como fallback

#### ⚠️ Problema 6: selenium_extractor.py no se usa
**Ubicación**: `scripts/selenium_extractor.py`

**Síntoma**: Módulo completo con funciones de extracción pero no se usa en linkedin_applier

**Causa Raíz**:
- Parece ser un módulo en desarrollo o abandonado
- Tiene lógica duplicada con los handlers de linkedin_applier
- No está integrado en el flujo principal

**Solución Propuesta**:
- Eliminar o integrar completamente
- Si se integra, refactorizar handlers para usar SeleniumExtractor

### 5.3 Problemas Menores (Mejoras)

#### ℹ️ Problema 7: Descripciones de trabajo incompletas
**Ubicación**: `linkedin_scraper.py` línea ~450

**Síntoma**: No puede expandir "mostrar más" en descripciones

**Solución Propuesta**:
```python
# Buscar y clickear botón "mostrar más"
try:
    expand_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label*='mostrar más'], button[aria-label*='Show more']")
    expand_button.click()
    time.sleep(1)
except:
    pass  # Si no hay botón, continuar
```

#### ℹ️ Problema 8: ia_integration vs ia_classifier duplicados
**Ubicación**: Ambos archivos

**Síntoma**: Funciones similares en ambos módulos

**Solución Propuesta**:
- Mantener `ia_integration` como interfaz única
- `ia_classifier` solo para lógica interna
- Nunca llamar directamente a `ia_classifier` desde linkedin_applier


---

## 6. Propuesta de Modularización

### 6.1 Estructura Propuesta

```
scripts/
├── core/
│   ├── __init__.py
│   ├── config.py              # Config, Logger (desde utils.py)
│   └── credentials.py         # credentials_manager.py
│
├── linkedin/
│   ├── __init__.py
│   ├── auth.py                # Login, cookies, sesión
│   ├── scraper.py             # Búsqueda de trabajos
│   ├── navigator.py           # Navegación (abrir modal, click botones)
│   └── form_processor.py     # Procesamiento de formularios
│
├── form_handlers/
│   ├── __init__.py
│   ├── base_handler.py        # Clase base para handlers
│   ├── text_handler.py        # handle_text_question
│   ├── textarea_handler.py    # handle_open_question
│   ├── radio_handler.py       # handle_radio_questions
│   ├── dropdown_handler.py    # handle_dropdown_questions
│   └── upload_handler.py      # handle_cv_upload
│
├── ai/
│   ├── __init__.py
│   ├── integration.py         # IAIntegration (interfaz única)
│   ├── classifier.py          # AIClassifier (lógica interna)
│   ├── openrouter.py          # OpenRouterClient
│   └── cv_processor.py        # CVProcessor
│
├── storage/
│   ├── __init__.py
│   ├── sheets_manager.py      # GoogleSheetsManager
│   └── local_storage.py       # Manejo de JSON local
│
├── notifications/
│   ├── __init__.py
│   └── telegram.py            # TelegramNotifier
│
└── utils/
    ├── __init__.py
    ├── selenium_helpers.py    # Funciones auxiliares Selenium
    └── text_utils.py          # clean_text, etc.
```

### 6.2 Módulos Nuevos Propuestos

#### 6.2.1 linkedin/auth.py
**Responsabilidad**: Gestión de autenticación y sesión

```python
class LinkedInAuth:
    def __init__(self, driver, config, logger):
        self.driver = driver
        self.config = config
        self.logger = logger
        self.cookies_file = Path("data/cookies/linkedin_cookies.json")
    
    def login(self, email, password) -> bool:
        """Inicia sesión en LinkedIn"""
        pass
    
    def load_cookies(self) -> bool:
        """Carga cookies guardadas"""
        pass
    
    def save_cookies(self):
        """Guarda cookies de sesión"""
        pass
    
    def is_logged_in(self) -> bool:
        """Verifica si está logueado"""
        pass
    
    def refresh_session(self):
        """Refresca la sesión si expiró"""
        pass
```

#### 6.2.2 linkedin/navigator.py
**Responsabilidad**: Navegación y detección de elementos

```python
class LinkedInNavigator:
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
    
    def open_easy_apply_modal(self, job_url) -> bool:
        """Abre el modal de Easy Apply"""
        # Busca botón con múltiples estrategias
        # Verifica que modal está visible
        # Retorna True si éxito
        pass
    
    def is_modal_open(self) -> bool:
        """Verifica si el modal está abierto y visible"""
        pass
    
    def find_next_button(self) -> Optional[WebElement]:
        """Encuentra botón Siguiente/Revisar/Enviar"""
        # Busca dentro del modal
        # Filtra botones "Volver"
        # Retorna elemento o None
        pass
    
    def click_button_safe(self, button) -> bool:
        """Click seguro con retry y JavaScript fallback"""
        pass
    
    def scroll_to_element(self, element):
        """Scroll para hacer elemento visible"""
        pass
```


#### 6.2.3 linkedin/form_processor.py
**Responsabilidad**: Orquestación del procesamiento de formularios

```python
class FormProcessor:
    def __init__(self, driver, config, logger, ia_integration):
        self.driver = driver
        self.config = config
        self.logger = logger
        self.ia = ia_integration
        self.handlers = self._init_handlers()
    
    def _init_handlers(self):
        """Inicializa todos los handlers"""
        return {
            'text': TextHandler(self.driver, self.config, self.logger, self.ia),
            'textarea': TextareaHandler(self.driver, self.config, self.logger, self.ia),
            'radio': RadioHandler(self.driver, self.config, self.logger, self.ia),
            'dropdown': DropdownHandler(self.driver, self.config, self.logger, self.ia),
            'upload': UploadHandler(self.driver, self.config, self.logger)
        }
    
    def process_form(self, job, result) -> bool:
        """Procesa formulario multi-paso"""
        max_steps = 10
        current_step = 0
        seen_questions = set()
        
        while current_step < max_steps:
            current_step += 1
            
            # Procesar paso actual
            success = self.process_current_step(job, result, seen_questions)
            if not success:
                return False
            
            # Buscar botón siguiente
            next_button = self.find_next_button()
            if not next_button:
                return False
            
            # Click y verificar si es submit
            if self.is_submit_button(next_button):
                next_button.click()
                return True
            
            next_button.click()
            time.sleep(1)
        
        return False
    
    def process_current_step(self, job, result, seen_questions) -> bool:
        """Procesa todos los campos del paso actual"""
        # Llamar a cada handler
        for handler_type, handler in self.handlers.items():
            handler.process(job, result, seen_questions)
        
        return True
```

#### 6.2.4 form_handlers/base_handler.py
**Responsabilidad**: Clase base para todos los handlers

```python
class BaseFormHandler:
    def __init__(self, driver, config, logger, ia_integration=None):
        self.driver = driver
        self.config = config
        self.logger = logger
        self.ia = ia_integration
        self.answers = config.load_json_config('respuestas_comunes.json')
    
    def process(self, job, result, seen_questions):
        """Método abstracto - implementar en subclases"""
        raise NotImplementedError
    
    def get_ia_answer(self, question_text, question_type, options=None):
        """Obtiene respuesta de IA con validación"""
        if not self.ia or not self.ia.enabled:
            return None, 0
        
        ia_result = self.ia.answer_question(
            question_text=question_text,
            question_type=question_type,
            options=options
        )
        
        answer = ia_result.get('answer', '')
        confidence = ia_result.get('confidence', 0)
        
        # Validar respuesta
        if "información no disponible" in answer.lower():
            return None, 0
        
        return answer, confidence
    
    def get_config_answer(self, question_text):
        """Busca respuesta en configuración"""
        # Lógica de find_answer_for_question
        pass
    
    def should_mark_manual(self, confidence, threshold=0.7):
        """Determina si debe marcarse como manual"""
        return confidence < threshold
    
    def log_answer(self, result, question_text, answer, source, confidence, auto_submit):
        """Registra respuesta en result"""
        if 'answers_log' not in result:
            result['answers_log'] = {}
        
        result['answers_log'][question_text] = {
            'answer': answer,
            'source': source,
            'ia_confidence': confidence,
            'ia_auto': auto_submit
        }
```


#### 6.2.5 form_handlers/text_handler.py
**Responsabilidad**: Manejo de inputs type="text"

```python
class TextHandler(BaseFormHandler):
    def process(self, job, result, seen_questions):
        """Procesa todos los inputs type='text' del formulario"""
        text_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
        
        for text_input in text_inputs:
            self._process_single_input(text_input, result, seen_questions)
    
    def _process_single_input(self, text_input, result, seen_questions):
        """Procesa un input individual"""
        # Extraer pregunta
        question_text = self._extract_question_text(text_input)
        if not question_text or question_text in seen_questions:
            return
        
        seen_questions.add(question_text)
        
        # Detectar tipo esperado
        expected_type = self._detect_input_type(text_input)
        
        # Obtener respuesta (IA primero, luego config)
        answer, confidence = self.get_ia_answer(question_text, f"text_{expected_type}")
        
        if not answer:
            answer = self.get_config_answer(question_text)
            confidence = 1.0 if answer else 0
        
        # Validar confianza
        if self.should_mark_manual(confidence):
            result['status'] = 'MANUAL'
            result['manual_questions'].append({
                'question': question_text,
                'confidence': confidence
            })
            return
        
        # Rellenar campo
        if answer:
            self._fill_input(text_input, answer, expected_type)
            self.log_answer(result, question_text, answer, 'IA' if confidence < 1 else 'Config', confidence, confidence >= 0.85)
    
    def _extract_question_text(self, text_input):
        """Extrae texto de pregunta del input"""
        # Lógica actual de handle_text_question
        pass
    
    def _detect_input_type(self, text_input):
        """Detecta tipo esperado (number, date, text)"""
        # Lógica actual de detect_input_type
        pass
    
    def _fill_input(self, text_input, answer, expected_type):
        """Rellena input con validación de tipo"""
        # Si es number, convertir a int
        if expected_type == 'number':
            try:
                answer = str(int(float(answer)))
            except:
                pass
        
        text_input.clear()
        text_input.send_keys(answer)
```

### 6.3 Beneficios de la Modularización

#### ✅ Separación de Responsabilidades
- Cada módulo tiene una responsabilidad clara
- Fácil de entender qué hace cada archivo
- Reduce acoplamiento entre componentes

#### ✅ Facilita Testing
- Cada handler se puede testear independientemente
- Mocks más fáciles de crear
- Tests unitarios por módulo

#### ✅ Reutilización de Código
- BaseFormHandler evita duplicación
- Funciones auxiliares compartidas en utils/
- Lógica de IA centralizada

#### ✅ Mantenibilidad
- Cambios en un handler no afectan otros
- Fácil agregar nuevos tipos de campos
- Debugging más simple (archivos pequeños)

#### ✅ Escalabilidad
- Fácil agregar nuevos handlers
- Fácil agregar nuevas fuentes de respuestas
- Fácil agregar nuevos tipos de autenticación


---

## 7. Plan de Implementación

### Fase 1: Fixes Críticos (Prioridad Alta) 🔴
**Objetivo**: Hacer que las postulaciones funcionen

#### 1.1 Fix: Detección de Modal
- [ ] Mejorar `is_modal_open()` para verificar visibilidad real
- [ ] Buscar elementos SOLO dentro del modal
- [ ] Filtrar dropdown de idioma (es_ES) que está en página principal

#### 1.2 Fix: Búsqueda de Botón Siguiente
- [ ] Buscar botones dentro del modal específicamente
- [ ] Usar texto del botón + aria-label combinados
- [ ] Filtrar botones "Volver"
- [ ] Scroll al botón antes de click

#### 1.3 Fix: Procesamiento de Todos los Campos
- [ ] Asegurar que todos los handlers se ejecutan en cada paso
- [ ] No salir del loop hasta procesar todos los campos visibles
- [ ] Separar `seen_questions` por tipo si es necesario

**Tiempo Estimado**: 4-6 horas

### Fase 2: Mejoras de Calidad (Prioridad Media) 🟡
**Objetivo**: Mejorar precisión de respuestas

#### 2.1 Implementar Threshold de Confianza
- [ ] Marcar como MANUAL si confidence < 0.7
- [ ] Guardar preguntas de baja confianza en result
- [ ] Agregar a Google Sheets para revisión manual

#### 2.2 Mejorar Extracción de Descripciones
- [ ] Implementar click en "mostrar más"
- [ ] Extraer descripción completa antes de clasificar
- [ ] Validar que descripción tiene > 200 chars

#### 2.3 Decidir sobre cv_by_keywords
- [ ] Evaluar precisión de keywords vs IA
- [ ] Decidir estrategia (IA primero, keywords fallback)
- [ ] Implementar estrategia elegida

**Tiempo Estimado**: 3-4 horas

### Fase 3: Refactorización (Prioridad Baja) 🟢
**Objetivo**: Código más mantenible

#### 3.1 Crear Estructura de Carpetas
- [ ] Crear carpetas: core/, linkedin/, form_handlers/, ai/, storage/, notifications/
- [ ] Mover archivos existentes a nuevas carpetas
- [ ] Actualizar imports

#### 3.2 Extraer LinkedInAuth
- [ ] Crear linkedin/auth.py
- [ ] Mover funciones de login, cookies, is_logged_in
- [ ] Actualizar linkedin_scraper.py y linkedin_applier.py

#### 3.3 Extraer LinkedInNavigator
- [ ] Crear linkedin/navigator.py
- [ ] Mover funciones de navegación y búsqueda de elementos
- [ ] Implementar find_next_button() mejorado

#### 3.4 Crear BaseFormHandler y Handlers
- [ ] Crear form_handlers/base_handler.py
- [ ] Crear handlers individuales (text, textarea, radio, dropdown, upload)
- [ ] Migrar lógica de linkedin_applier.py

#### 3.5 Crear FormProcessor
- [ ] Crear linkedin/form_processor.py
- [ ] Orquestar llamadas a handlers
- [ ] Simplificar process_application_form()

**Tiempo Estimado**: 8-10 horas

### Fase 4: Testing y Validación (Prioridad Alta) 🔴
**Objetivo**: Asegurar que todo funciona

#### 4.1 Tests Manuales
- [ ] Probar con 5 trabajos reales
- [ ] Verificar que modal se detecta correctamente
- [ ] Verificar que botones se encuentran
- [ ] Verificar que todos los campos se rellenan

#### 4.2 Tests Automatizados (Opcional)
- [ ] Tests unitarios para handlers
- [ ] Tests de integración para FormProcessor
- [ ] Tests end-to-end con trabajos de prueba

**Tiempo Estimado**: 4-6 horas

---

## 8. Resumen Ejecutivo

### Estado Actual
- ✅ Sistema de IA funcionando correctamente
- ✅ Scraping de trabajos funcional
- ✅ Integración con Google Sheets y Telegram
- ❌ Postulaciones NO funcionan (no encuentra botones)
- ⚠️ Detección de modal no es confiable
- ⚠️ No aplica threshold de confianza

### Problemas Principales
1. **No encuentra botón "Siguiente/Revisar"** - Selectores incorrectos
2. **Detección de modal no confiable** - Busca en toda la página
3. **No marca preguntas como MANUAL** - Falta lógica de threshold

### Solución Recomendada
1. **Corto Plazo** (1-2 días): Fixes críticos (Fase 1)
2. **Mediano Plazo** (3-5 días): Mejoras de calidad (Fase 2)
3. **Largo Plazo** (1-2 semanas): Refactorización completa (Fase 3)

### Próximos Pasos Inmediatos
1. Fix detección de modal (buscar solo dentro de `div[role='dialog']`)
2. Fix búsqueda de botón (buscar dentro del modal, usar texto + aria-label)
3. Probar con 3-5 trabajos reales
4. Iterar hasta que funcione

---

**Fecha**: 20 de Febrero, 2026  
**Versión**: 1.0  
**Autor**: Análisis del código existente
