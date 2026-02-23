# 📊 Diagramas de Flujo - LinkedIn Job Automator

## 1. Flujo General del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                         N8N WORKFLOW                             │
│                    (Trigger: 09:00 AM diario)                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PASO 1: SCRAPING                              │
│                  linkedin_scraper.py                             │
│                                                                  │
│  1. Login con cookies                                            │
│  2. Buscar trabajos (keywords + location)                        │
│  3. Extraer datos (título, empresa, descripción, URL)           │
│  4. Verificar Easy Apply                                         │
│  5. Deduplica contra Google Sheets                              │
│  6. Guardar en jobs_found.json (is_new: true)                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PASO 2: APLICACIÓN                            │
│                  linkedin_applier.py                             │
│                                                                  │
│  Para cada trabajo nuevo:                                        │
│    1. Navegar a URL                                              │
│    2. Clasificar trabajo (keywords + IA)                         │
│    3. Abrir modal Easy Apply                                     │
│    4. Procesar formulario multi-paso                             │
│    5. Guardar resultado                                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PASO 3: SINCRONIZACIÓN                        │
│                google_sheets_manager.py                          │
│                                                                  │
│  1. Agregar aplicaciones a Google Sheets                         │
│  2. Actualizar dashboard con métricas                            │
│  3. Marcar preguntas manuales para revisión                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PASO 4: NOTIFICACIÓN                          │
│                  telegram_notifier.py                            │
│                                                                  │
│  1. Enviar resumen de aplicaciones                               │
│  2. Enviar estadísticas de IA                                    │
│  3. Alertar sobre errores                                        │
└─────────────────────────────────────────────────────────────────┘
```


## 2. Flujo Detallado de Aplicación (linkedin_applier.py)

```
apply_to_job(job)
│
├─> 1. CARGAR PÁGINA
│   ├─> driver.get(job['url'])
│   ├─> Esperar 3 segundos
│   └─> Extraer descripción completa
│       ├─> Buscar botón "mostrar más"
│       ├─> Click para expandir
│       └─> Extraer texto completo
│
├─> 2. CLASIFICACIÓN
│   ├─> select_cv_by_keywords(title, description)  [PRIORIDAD 1]
│   │   └─> Retorna: "software" o "consultoria"
│   │
│   └─> ia.classify_job(title, description, requirements)  [SOLO STATS]
│       └─> Retorna: {job_type, confidence, recommended_cv, ...}
│
├─> 3. ABRIR MODAL EASY APPLY
│   ├─> Buscar botón con selectores:
│   │   ├─> "button.jobs-apply-button"
│   │   ├─> "button[aria-label*='Solicitud sencilla']"
│   │   ├─> "button[aria-label*='Easy Apply']"
│   │   └─> ... (5 selectores más)
│   │
│   ├─> Intentar click normal
│   ├─> Si falla: JavaScript click
│   │
│   └─> VERIFICAR MODAL ABIERTO ⚠️ PROBLEMA AQUÍ
│       ├─> Buscar div[role='dialog']
│       ├─> Buscar elementos de formulario
│       └─> Si no hay: return error
│
└─> 4. PROCESAR FORMULARIO
    └─> process_application_form(job, result)
        │
        └─> LOOP (max 10 pasos):
            │
            ├─> fill_current_form_step(job, result, seen_questions)
            │   │
            │   ├─> handle_cv_upload()
            │   │   └─> Subir CV apropiado
            │   │
            │   ├─> handle_text_question() - Para cada input[type="text"]
            │   │   ├─> Extraer pregunta
            │   │   ├─> detect_input_type() (number, date, text)
            │   │   ├─> ia.answer_question()
            │   │   ├─> Si falla: find_answer_for_question()
            │   │   └─> Rellenar campo
            │   │
            │   ├─> handle_open_question() - Para cada textarea
            │   │   ├─> Extraer pregunta
            │   │   ├─> ia.answer_question()
            │   │   ├─> Si falla: find_answer_for_question()
            │   │   └─> Rellenar campo
            │   │
            │   ├─> handle_radio_questions() - Para todos los radio groups
            │   │   ├─> Para cada grupo:
            │   │   │   ├─> Extraer pregunta y opciones
            │   │   │   ├─> ia.answer_question()
            │   │   │   ├─> Validar respuesta en opciones
            │   │   │   ├─> Si falla: find_answer_for_question()
            │   │   │   └─> Click en radio
            │   │   └─> ...
            │   │
            │   └─> handle_dropdown_questions() - Para todos los selects
            │       ├─> Para cada select:
            │       │   ├─> Extraer pregunta y opciones
            │       │   ├─> ia.answer_question()
            │       │   ├─> Validar respuesta en opciones
            │       │   ├─> Si falla: find_answer_for_question()
            │       │   └─> Seleccionar opción
            │       └─> ...
            │
            ├─> BUSCAR BOTÓN SIGUIENTE ⚠️ PROBLEMA AQUÍ
            │   ├─> Intentar selectores:
            │   │   ├─> "aria-label=Revisar"
            │   │   ├─> "aria-label=Review"
            │   │   ├─> "aria-label=Enviar"
            │   │   ├─> "aria-label=Submit"
            │   │   ├─> "aria-label=Continuar"
            │   │   ├─> "aria-label=Continue"
            │   │   ├─> "aria-label=Next"
            │   │   └─> "aria-label=Siguiente"
            │   │
            │   └─> Si no encuentra: return False
            │
            ├─> CLICK EN BOTÓN
            │   ├─> Scroll al botón
            │   ├─> Click
            │   └─> Esperar 0.5s
            │
            └─> SI ES BOTÓN "ENVIAR":
                └─> return True (éxito)
```


## 3. Flujo de Respuesta a Preguntas (con IA)

```
handle_text_question(text_input, result, seen_questions, new_questions)
│
├─> 1. EXTRAER PREGUNTA
│   ├─> Buscar label asociado (por 'for' attribute)
│   ├─> Si no: Buscar label en contenedor padre
│   ├─> Si no: Usar placeholder o aria-label
│   └─> Limpiar texto (quitar asteriscos, etc.)
│
├─> 2. VALIDAR PREGUNTA
│   ├─> ¿Es pregunta válida? (len > 5)
│   ├─> ¿No es campo genérico? (email, teléfono, etc.)
│   ├─> ¿Ya fue vista? (en seen_questions)
│   └─> Si no válida: return False
│
├─> 3. DETECTAR TIPO ESPERADO
│   └─> detect_input_type(text_input)
│       ├─> Check type attribute
│       ├─> Check inputmode attribute
│       ├─> Check pattern regex
│       ├─> Check placeholder text
│       └─> Retorna: "number", "date", "text", etc.
│
├─> 4. OBTENER RESPUESTA IA
│   └─> ia.answer_question(question_text, question_type, options, previous_answers)
│       │
│       └─> ia_integration.answer_question()
│           │
│           └─> ia_classifier.answer_question()
│               │
│               └─> openrouter_client.answer_question()
│                   │
│                   ├─> Construir prompt con:
│                   │   ├─> Pregunta
│                   │   ├─> Tipo esperado
│                   │   ├─> Contexto CV
│                   │   └─> Respuestas previas
│                   │
│                   ├─> API Call a Llama 3.3 70B
│                   │
│                   └─> Retorna:
│                       {
│                         answer: "...",
│                         confidence: 0.92,
│                         reasoning: "...",
│                         sources: ["CV: Python 5 años"],
│                         auto_submit: true
│                       }
│
├─> 5. VALIDAR RESPUESTA IA
│   ├─> ¿Es "información no disponible"?
│   │   ├─> Sí: low_confidence_count++
│   │   └─> Si count >= 3: ABORTAR (status = MANUAL)
│   │
│   ├─> ¿Es pregunta de años?
│   │   └─> Convertir a número entero
│   │
│   └─> ¿Confianza >= 0.85?
│       ├─> Sí: Rellenar campo
│       └─> No: Buscar en config
│
├─> 6. FALLBACK: BUSCAR EN CONFIG
│   └─> find_answer_for_question(question_text)
│       ├─> Buscar en respuestas_comunes.json
│       ├─> Usar regex patterns
│       └─> Retorna respuesta o None
│
├─> 7. RELLENAR CAMPO
│   ├─> text_input.clear()
│   ├─> text_input.send_keys(answer)
│   └─> Verificar que se escribió
│
└─> 8. GUARDAR EN LOG
    └─> result['answers_log'][question_text] = {
          answer: "...",
          source: "IA (Auto)" | "Config",
          ia_confidence: 0.92,
          ia_auto: true
        }
```


## 4. Arquitectura de Módulos IA

```
┌─────────────────────────────────────────────────────────────────┐
│                      linkedin_applier.py                         │
│                                                                  │
│  - apply_to_job()                                                │
│  - process_application_form()                                    │
│  - handle_text_question()                                        │
│  - handle_radio_questions()                                      │
│  - handle_dropdown_questions()                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ self.ia.answer_question()
                         │ self.ia.classify_job()
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ia_integration.py                           │
│                     (Interfaz Unificada)                         │
│                                                                  │
│  - classify_job()                                                │
│  - answer_question()                                             │
│  - set_cv_type()                                                 │
│  - get_stats()                                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ self.classifier.answer_question()
                         │ self.classifier.classify_job()
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ia_classifier.py                            │
│                    (Lógica de Clasificación)                     │
│                                                                  │
│  - classify_job()                                                │
│  - answer_question()                                             │
│  - extract_best_option()                                         │
│  - evaluate_answer_quality()                                     │
│  - get_stats()                                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ self.ai_client.classify_job()
                         │ self.ai_client.answer_question()
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    openrouter_client.py                          │
│                      (Cliente API)                               │
│                                                                  │
│  - call()                                                        │
│  - classify_job()                                                │
│  - answer_question()                                             │
│  - extract_json_response()                                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTP POST
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OpenRouter API                                │
│                  (Llama 3.3 70B Instruct)                        │
│                                                                  │
│  - Recibe prompt con contexto CV                                 │
│  - Genera respuesta JSON                                         │
│  - Retorna con confidence score                                  │
└─────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                      cv_processor.py                             │
│                   (Gestión de Contexto CV)                       │
│                                                                  │
│  - load_or_create()                                              │
│  - extract_pdf_to_json()                                         │
│  - get_context_as_string()                                       │
└─────────────────────────────────────────────────────────────────┘
                         │
                         │ Carga contexto
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              data/curriculum_context.json                        │
│                                                                  │
│  {                                                               │
│    personal_info: {...},                                         │
│    summary: "...",                                               │
│    skills: ["Python", "Django", ...],                            │
│    experience: [{...}, {...}],                                   │
│    projects: [{...}],                                            │
│    certifications: [{...}]                                       │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
```


## 5. Problemas Identificados en el Flujo

### Problema 1: Detección de Modal
```
FLUJO ACTUAL (INCORRECTO):
apply_to_job()
├─> Click en "Solicitud sencilla"
├─> Esperar 1.5s
└─> Verificar modal:
    ├─> Buscar div[role='dialog'] ✅
    ├─> Buscar input, textarea, select EN TODA LA PÁGINA ❌
    │   └─> Encuentra dropdown de idioma (es_ES) en página principal
    └─> Dice "Modal abierto" pero NO LO ESTÁ ❌

FLUJO CORRECTO (PROPUESTO):
apply_to_job()
├─> Click en "Solicitud sencilla"
├─> Esperar 1.5s
└─> Verificar modal:
    ├─> Buscar div[role='dialog'].artdeco-modal--layer-default ✅
    ├─> Verificar que está VISIBLE (not display:none) ✅
    ├─> Verificar z-index > 1000 (está en primer plano) ✅
    ├─> Buscar elementos DENTRO del modal ✅
    │   └─> modal.find_elements(By.CSS_SELECTOR, "input, textarea, select")
    ├─> Filtrar elementos del header (language selector) ✅
    └─> Si len(valid_elements) > 0: Modal abierto ✅
```

### Problema 2: Búsqueda de Botón Siguiente
```
FLUJO ACTUAL (INCORRECTO):
process_application_form()
└─> Buscar botón:
    ├─> Buscar por aria-label EXACTO ❌
    │   └─> "aria-label=Revisar" (no encuentra si es "Revisar tu solicitud")
    ├─> Buscar EN TODA LA PÁGINA ❌
    │   └─> Puede encontrar botones fuera del modal
    └─> Timeout de 1 segundo por selector ❌
        └─> Muy poco tiempo si hay lag

FLUJO CORRECTO (PROPUESTO):
process_application_form()
└─> Buscar botón:
    ├─> Obtener modal: driver.find_element(By.CSS_SELECTOR, "div[role='dialog']") ✅
    ├─> Buscar TODOS los botones dentro del modal ✅
    │   └─> modal.find_elements(By.TAG_NAME, "button")
    ├─> Para cada botón: ✅
    │   ├─> Obtener texto: button.text.lower()
    │   ├─> Obtener aria-label: button.get_attribute('aria-label').lower()
    │   ├─> Combinar: f"{text} {aria}"
    │   ├─> Buscar palabras clave: ['siguiente', 'next', 'revisar', 'review', 'enviar', 'submit']
    │   └─> Filtrar "Volver", "Back", "Cancel"
    └─> Retornar primer botón válido ✅
```

### Problema 3: Procesamiento de Campos Mezclados
```
FLUJO ACTUAL (INCORRECTO):
fill_current_form_step()
├─> handle_text_question() - Procesa TODOS los input[type="text"]
│   └─> Marca preguntas en seen_questions
├─> handle_dropdown_questions() - Procesa TODOS los selects
│   └─> Algunas preguntas ya están en seen_questions ❌
│       └─> Las salta, no las responde ❌
└─> Resultado: Solo responde un tipo de campo

FLUJO CORRECTO (PROPUESTO):
fill_current_form_step()
├─> Obtener TODOS los elementos del formulario
│   ├─> inputs = modal.find_elements(By.CSS_SELECTOR, "input")
│   ├─> textareas = modal.find_elements(By.TAG_NAME, "textarea")
│   └─> selects = modal.find_elements(By.TAG_NAME, "select")
│
├─> Para cada elemento:
│   ├─> Determinar tipo (text, radio, dropdown, etc.)
│   ├─> Llamar handler apropiado
│   └─> Trackear por (tipo + pregunta) en seen_questions
│       └─> seen_questions.add(f"{tipo}:{pregunta}")
│
└─> Resultado: Responde TODOS los campos del formulario
```


## 6. Propuesta de Arquitectura Modular

```
┌─────────────────────────────────────────────────────────────────┐
│                      linkedin_applier.py                         │
│                      (Orquestador Principal)                     │
│                                                                  │
│  - apply_to_job()                                                │
│  - main()                                                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Usa
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    linkedin/navigator.py                         │
│                    (Navegación y Detección)                      │
│                                                                  │
│  - open_easy_apply_modal()                                       │
│  - is_modal_open()                                               │
│  - find_next_button()                                            │
│  - click_button_safe()                                           │
│  - scroll_to_element()                                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  linkedin/form_processor.py                      │
│                  (Orquestador de Formulario)                     │
│                                                                  │
│  - process_form()                                                │
│  - process_current_step()                                        │
│  - is_submit_button()                                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Usa
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  form_handlers/base_handler.py                   │
│                      (Clase Base)                                │
│                                                                  │
│  - process()                                                     │
│  - get_ia_answer()                                               │
│  - get_config_answer()                                           │
│  - should_mark_manual()                                          │
│  - log_answer()                                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Hereda
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              form_handlers/text_handler.py                       │
│              form_handlers/textarea_handler.py                   │
│              form_handlers/radio_handler.py                      │
│              form_handlers/dropdown_handler.py                   │
│              form_handlers/upload_handler.py                     │
│                                                                  │
│  Cada uno implementa:                                            │
│  - process(job, result, seen_questions)                          │
│  - _extract_question_text()                                      │
│  - _fill_field()                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      ai/integration.py                           │
│                    (Interfaz Única de IA)                        │
│                                                                  │
│  - classify_job()                                                │
│  - answer_question()                                             │
│  - set_cv_type()                                                 │
│  - get_stats()                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Beneficios de la Nueva Arquitectura

1. **Separación de Responsabilidades**
   - Navigator: Solo navegación y detección de elementos
   - FormProcessor: Solo orquestación de formulario
   - Handlers: Solo procesamiento de un tipo de campo
   - IAIntegration: Solo comunicación con IA

2. **Facilita Testing**
   - Cada módulo se puede testear independientemente
   - Mocks más fáciles de crear
   - Tests unitarios por handler

3. **Reutilización de Código**
   - BaseFormHandler evita duplicación
   - Funciones auxiliares compartidas
   - Lógica de IA centralizada

4. **Mantenibilidad**
   - Cambios en un handler no afectan otros
   - Fácil agregar nuevos tipos de campos
   - Debugging más simple (archivos pequeños)

5. **Escalabilidad**
   - Fácil agregar nuevos handlers
   - Fácil agregar nuevas fuentes de respuestas
   - Fácil agregar nuevos tipos de autenticación

---

**Fecha**: 20 de Febrero, 2026  
**Versión**: 1.0
