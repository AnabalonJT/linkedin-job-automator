# Plan de Implementación: Mejoras al Sistema de Automatización de Postulaciones LinkedIn

## Overview

Este plan implementa mejoras críticas al sistema automatizado de postulaciones en LinkedIn (`linkedin_applier.py`). El enfoque es incremental, priorizando funcionalidad crítica primero (detección de modal, IA para CV y preguntas, sistema de confianza), seguido por mejoras de robustez y observabilidad.

La implementación se basa en:
- **Python** con Selenium WebDriver para automatización
- **JavaScript** para interacción robusta con el modal dinámico
- **OpenRouter API** para clasificación inteligente con IA
- **Hypothesis** para property-based testing (100 iteraciones mínimo)
- **Google Sheets API** para tracking
- **Telegram Bot API** para notificaciones

## Tasks

- [x] 1. Configurar estructura base y modelos de datos
  - Crear archivo `scripts/models.py` con dataclasses: FormField, CVRecommendation, QuestionAnswer, ApplicationDecision, ProcessedJob, ApplicationResult
  - Agregar type hints completos y docstrings
  - _Requisitos: 3.1, 4.1, 5.3, 7.4, 8.1, 15.1_

- [ ]* 1.1 Escribir property tests para modelos de datos
  - **Property 11: CV Recommendation Format** - Validar que CVRecommendation contenga cv_type válido, confidence 0.0-1.0, y reasoning
  - **Property 19: Confidence Value Range** - Validar que todos los valores de confianza estén entre 0.0-1.0
  - **Valida: Requisitos 5.3, 5.4, 8.1**

- [x] 2. Implementar ModalDetector con JavaScript y selectores fallback
  - [x] 2.1 Crear clase ModalDetector en `scripts/modal_detector.py`
    - Implementar `wait_for_modal()` usando JavaScript con polling cada 500ms
    - Implementar lista de selectores fallback: `div[data-test-modal-id="easy-apply-modal"]`, `div[data-test-modal-container]`, `div.jobs-easy-apply-modal`, `div[role="dialog"]`
    - Implementar `is_modal_visible()` para verificar visibilidad
    - Timeout configurable (default 15 segundos)
    - _Requisitos: 3.1, 3.2, 3.5_

  - [ ]* 2.2 Escribir property test para detección de modal
    - **Property 5: Modal Detection with Fallback Selectors** - Verificar que al menos un selector detecte el modal
    - **Valida: Requisitos 3.2**

  - [ ]* 2.3 Escribir unit tests para ModalDetector
    - Test con HTML conocido conteniendo cada selector
    - Test de timeout cuando modal no aparece
    - Test de múltiples selectores fallback

- [x] 3. Implementar FormFieldDetector para identificación de campos
  - [x] 3.1 Crear clase FormFieldDetector en `scripts/form_field_detector.py`
    - Implementar `detect_fields()` que busca SOLO dentro del contexto del modal
    - Mapear tipos de campo: text input, email, phone, dropdown, textarea, radio, checkbox, file upload
    - Usar selectores específicos de LinkedIn: `input[data-test-single-line-text-form-component]`, `select[data-test-text-entity-list-form-select]`
    - Implementar `get_field_purpose()` usando label, placeholder, aria-label, id
    - Logging de cada campo detectado con tipo y propósito
    - _Requisitos: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 3.2 Escribir property tests para FormFieldDetector
    - **Property 6: Form Field Scoping** - Verificar que solo se detecten campos dentro del modal
    - **Property 8: Field Type Detection** - Verificar detección correcta de todos los tipos de campo
    - **Property 9: Field Purpose Identification** - Verificar identificación de propósito usando metadata
    - **Valida: Requisitos 3.3, 4.1, 4.3, 4.4**

  - [ ]* 3.3 Escribir unit tests para FormFieldDetector
    - Test de detección de cada tipo de campo
    - Test de extracción de propósito desde diferentes fuentes (label, placeholder, aria-label)
    - Test de ignorar elementos fuera del modal

- [ ] 4. Checkpoint - Verificar detección de modal y campos
  - Ejecutar tests de ModalDetector y FormFieldDetector
  - Verificar que los tests pasen
  - Preguntar al usuario si hay dudas o ajustes necesarios

- [x] 5. Implementar CVSelector con integración OpenRouter
  - [x] 5.1 Crear clase CVSelector en `scripts/cv_selector.py`
    - Implementar `select_cv()` que llama a OpenRouter con job_title y job_description
    - Implementar `detect_language()` para detectar idioma (en/es)
    - Definir CV_MAPPING: (software, en) → "CV Software Engineer Anabalon.pdf", (engineer, es) → "CV Automatización_Data Anabalón.pdf"
    - Parsear respuesta JSON de OpenRouter: cv_type, language, confidence, reasoning
    - Manejo de errores: rate limit (429) con exponential backoff, timeouts
    - _Requisitos: 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.5_

  - [ ]* 5.2 Escribir property tests para CVSelector
    - **Property 13: Language-Based CV Selection** - Verificar selección correcta según tipo y idioma
    - **Valida: Requisitos 6.1, 6.2, 6.3, 6.5**

  - [ ]* 5.3 Escribir unit tests para CVSelector
    - Test de detección de idioma con textos en inglés y español
    - Test de mapeo correcto de CV según tipo y idioma
    - Test de manejo de errores de API (429, timeout)
    - Mock de OpenRouter API con respuestas predefinidas

- [x] 6. Implementar QuestionHandler para respuestas con IA
  - [x] 6.1 Crear clase QuestionHandler en `scripts/question_handler.py`
    - Implementar `answer_question()` que llama a OpenRouter con question, field_type, cv_context, available_options
    - Parsear respuesta JSON: answer, confidence, reasoning, sources
    - Implementar `handle_special_questions()` para preguntas comunes:
      - Años de experiencia: responder solo número entero
      - Elegibilidad legal: responder "Yes"/"Sí" con confidence ≥ 0.95
      - Sponsorship: responder "No" con confidence ≥ 0.95
      - Salario: usar respuestas_comunes.json
    - Validar formato de respuesta según field_type (número para numeric, opción válida para dropdown)
    - Logging de pregunta y respuesta
    - _Requisitos: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 6.2 Escribir property tests para QuestionHandler
    - **Property 16: AI Response Format** - Verificar que respuesta JSON contenga todos los campos requeridos
    - **Property 17: Answer Format Validation** - Verificar que formato de respuesta coincida con tipo de campo
    - **Property 22: Experience Question Format** - Verificar respuesta numérica sin unidades
    - **Property 23: Legal Eligibility Response** - Verificar respuesta "Yes"/"Sí" con confidence ≥ 0.95
    - **Property 24: Sponsorship Response** - Verificar respuesta "No" con confidence ≥ 0.95
    - **Property 26: Numeric Answer Validation** - Verificar validación de respuestas numéricas
    - **Valida: Requisitos 7.4, 7.5, 9.1, 9.2, 9.3, 9.5**

  - [ ]* 6.3 Escribir unit tests para QuestionHandler
    - Test de respuestas especiales (experiencia, elegibilidad, sponsorship, salario)
    - Test de validación de formato según tipo de campo
    - Test de manejo de errores de API
    - Mock de OpenRouter API

- [ ] 7. Checkpoint - Verificar integración con IA
  - Ejecutar tests de CVSelector y QuestionHandler
  - Verificar que los mocks de OpenRouter funcionen correctamente
  - Preguntar al usuario si hay dudas sobre la integración con IA

- [x] 8. Implementar ConfidenceSystem para decisiones de auto-submit
  - [x] 8.1 Crear clase ConfidenceSystem en `scripts/confidence_system.py`
    - Implementar `evaluate_application()` que recibe lista de QuestionAnswer
    - Implementar `calculate_overall_confidence()` como promedio ponderado
    - Lógica de decisión:
      - Si todas las confidences ≥ 0.85 → SUBMIT
      - Si alguna confidence entre 0.65-0.85 → UNCERTAIN
      - Si alguna confidence < 0.65 → MANUAL
    - Umbrales configurables via variables de entorno (HIGH_THRESHOLD=0.85, LOW_THRESHOLD=0.65)
    - Retornar ApplicationDecision con action, overall_confidence, reasoning, low_confidence_questions
    - _Requisitos: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ]* 8.2 Escribir property tests para ConfidenceSystem
    - **Property 20: Confidence-Based Decision Making** - Verificar decisión correcta según umbrales
    - **Valida: Requisitos 8.2, 8.3, 8.4**

  - [ ]* 8.3 Escribir unit tests para ConfidenceSystem
    - Test de decisión SUBMIT con todas las confidences altas
    - Test de decisión UNCERTAIN con confidences medias
    - Test de decisión MANUAL con confidences bajas
    - Test de umbrales configurables

- [x] 9. Implementar StateManager para persistencia y recuperación
  - [x] 9.1 Crear clase StateManager en `scripts/state_manager.py`
    - Implementar `load_state()` que lee data/logs/application_state.json
    - Implementar `save_job_state()` que guarda URL, timestamp, status
    - Implementar `is_job_processed()` para filtrar trabajos ya procesados
    - Implementar `cleanup_old_entries()` que elimina entradas > 30 días
    - Formato JSON: {"url": str, "status": str, "timestamp": ISO8601, "cv_used": str, "error_message": str}
    - _Requisitos: 15.1, 15.2, 15.3, 15.4, 15.5_

  - [ ]* 9.2 Escribir property tests para StateManager
    - **Property 46: State File Persistence** - Verificar estructura correcta del archivo de estado
    - **Property 47: State-Based Job Filtering** - Verificar filtrado correcto de trabajos procesados
    - **Property 48: Resumption After Interruption** - Verificar reanudación desde trabajo no procesado
    - **Property 49: State Cleanup** - Verificar eliminación de entradas > 30 días
    - **Valida: Requisitos 15.1, 15.2, 15.3, 15.4, 15.5**

  - [ ]* 9.3 Escribir unit tests para StateManager
    - Test de carga y guardado de estado
    - Test de filtrado de trabajos procesados
    - Test de limpieza de entradas antiguas
    - Test de manejo de archivo corrupto o inexistente

- [-] 10. Implementar GoogleSheetsUpdater para tracking
  - [x] 10.1 Crear clase GoogleSheetsUpdater en `scripts/google_sheets_updater.py`
    - Implementar `update_application()` que actualiza fila con job_id, status, cv_used, notes
    - Campos a actualizar: ID, fecha_aplicación, Empresa, Puesto, URL, Ubicación, tipo_aplicación, CV_Usado, Estado, Último_Update, Notas
    - Validar que Estado sea uno de: APPLIED, MANUAL, NO_DISPONIBLE, ERROR, INSEGURO
    - Implementar `add_confidence_notes()` para agregar preguntas con baja confianza
    - Lógica de notas:
      - Si Estado = INSEGURO → incluir low_confidence_questions
      - Si Estado = ERROR → incluir error_message
    - Manejo graceful de errores de API sin detener proceso
    - _Requisitos: 5.6, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

  - [ ]* 10.2 Escribir property tests para GoogleSheetsUpdater
    - **Property 27: Google Sheets Complete Update** - Verificar actualización de todos los campos requeridos
    - **Property 28: Status Value Validation** - Verificar que Estado sea uno de los valores válidos
    - **Property 29: Status-Based Notes** - Verificar notas según Estado
    - **Property 30: Google Sheets Error Resilience** - Verificar continuación tras error de API
    - **Valida: Requisitos 10.1, 10.2, 10.3, 10.4, 10.5, 10.6**

  - [ ]* 10.3 Escribir unit tests para GoogleSheetsUpdater
    - Test de actualización completa con todos los campos
    - Test de validación de valores de Estado
    - Test de notas según Estado (INSEGURO, ERROR)
    - Test de manejo de errores de API
    - Mock de Google Sheets API

- [x] 11. Implementar TelegramNotifier para notificaciones consolidadas
  - [x] 11.1 Crear clase TelegramNotifier en `scripts/telegram_notifier.py`
    - Implementar `accumulate_result()` que acumula resultados durante ejecución
    - Implementar `send_summary()` que envía UNA notificación al final
    - Contenido del resumen:
      - Total procesados, exitosos, manuales, no disponibles, errores
      - Estadísticas de IA: preguntas respondidas, tasa de automatización, confianza promedio
      - Lista de trabajos que requieren atención manual (MANUAL o INSEGURO)
    - Manejo graceful si Telegram no está configurado
    - _Requisitos: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [ ]* 11.2 Escribir property tests para TelegramNotifier
    - **Property 31: Result Accumulation** - Verificar acumulación de todos los resultados
    - **Property 32: Single Consolidated Notification** - Verificar envío de exactamente una notificación
    - **Property 33: Complete Notification Content** - Verificar contenido completo del resumen
    - **Property 34: Telegram Optional** - Verificar ejecución exitosa sin Telegram configurado
    - **Valida: Requisitos 11.1, 11.2, 11.3, 11.4, 11.5, 11.6**

  - [ ]* 11.3 Escribir unit tests para TelegramNotifier
    - Test de acumulación de resultados
    - Test de formato del mensaje de resumen
    - Test de envío único al final
    - Test de manejo cuando Telegram no está configurado
    - Mock de Telegram Bot API

- [ ] 12. Checkpoint - Verificar componentes auxiliares
  - Ejecutar tests de StateManager, GoogleSheetsUpdater, TelegramNotifier
  - Verificar que los mocks funcionen correctamente
  - Preguntar al usuario si hay dudas sobre persistencia y notificaciones

- [x] 13. Integrar componentes en LinkedInApplier
  - [x] 13.1 Refactorizar LinkedInApplier para usar nuevos componentes
    - Agregar imports de todos los componentes nuevos
    - Inicializar ModalDetector, FormFieldDetector, CVSelector, QuestionHandler, ConfidenceSystem, StateManager, GoogleSheetsUpdater, TelegramNotifier en `__init__`
    - Modificar `apply_to_job()` para:
      1. Verificar si trabajo ya fue procesado (StateManager)
      2. Detectar trabajos no disponibles (textos de cierre)
      3. Expandir descripción completa (botón "Ver más")
      4. Seleccionar CV con IA (CVSelector)
      5. Detectar modal con JavaScript (ModalDetector)
      6. Detectar campos del formulario (FormFieldDetector)
      7. Responder preguntas con IA (QuestionHandler)
      8. Evaluar confianza (ConfidenceSystem)
      9. Decidir acción (SUBMIT/UNCERTAIN/MANUAL)
      10. Actualizar Google Sheets (GoogleSheetsUpdater)
      11. Acumular resultado (TelegramNotifier)
      12. Guardar estado (StateManager)
    - _Requisitos: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 13.2 Implementar detección de trabajos no disponibles
    - Buscar textos de cierre: "No longer accepting applications", "Ya no se aceptan solicitudes", "This job is no longer available", "Closed"
    - Si se detecta, marcar como NO_DISPONIBLE y actualizar Google Sheets
    - Continuar con siguiente trabajo
    - _Requisitos: 1.1, 1.2, 1.3, 1.4_

  - [ ]* 13.3 Escribir property tests para detección de trabajos no disponibles
    - **Property 1: Job Availability Detection** - Verificar detección de indicadores de cierre
    - **Property 2: Unavailable Job Updates** - Verificar actualización correcta en Google Sheets
    - **Valida: Requisitos 1.1, 1.2, 1.3, 1.4**

  - [x] 13.4 Implementar expansión de descripción completa
    - Buscar botones con textos: "Ver más", "Show more", "See more"
    - Hacer clic usando JavaScript o Selenium
    - Esperar 1-2 segundos para carga
    - Extraer texto completo expandido
    - Pasar descripción completa a CVSelector
    - _Requisitos: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 13.5 Escribir property tests para expansión de descripción
    - **Property 3: Description Expansion Detection** - Verificar detección y clic en botón de expansión
    - **Property 4: Full Description to AI** - Verificar que descripción completa se pase a IA
    - **Valida: Requisitos 2.1, 2.2, 2.4, 2.5**

  - [x] 13.6 Implementar llenado de campos con JavaScript fallback
    - Intentar llenar campo con Selenium primero
    - Si falla, usar JavaScript como fallback: `driver.execute_script("arguments[0].value = arguments[1]", element, value)`
    - Logging de cada intento y resultado
    - _Requisitos: 3.4_

  - [ ]* 13.7 Escribir property test para JavaScript fallback
    - **Property 7: JavaScript Fallback for Field Filling** - Verificar uso de JavaScript cuando Selenium falla
    - **Valida: Requisitos 3.4**

  - [x] 13.8 Implementar logging de campos detectados
    - Para cada campo detectado, loggear tipo y propósito
    - Formato: "Campo detectado: tipo={field_type}, propósito={purpose}"
    - _Requisitos: 4.5_

  - [ ]* 13.9 Escribir property test para logging de campos
    - **Property 10: Field Detection Logging** - Verificar logging de tipo y propósito
    - **Valida: Requisitos 4.5**

  - [x] 13.10 Implementar registro de CV usado
    - Después de seleccionar CV, guardar en variable para Google Sheets
    - Actualizar campo CV_Usado en Google Sheets
    - _Requisitos: 5.6_

  - [ ]* 13.11 Escribir property test para registro de CV
    - **Property 12: CV Usage Recording** - Verificar registro en Google Sheets
    - **Valida: Requisitos 5.6**

  - [x] 13.12 Implementar extracción de preguntas y contexto
    - Para cada pregunta, extraer texto y tipo de campo
    - Enviar pregunta + CV context a QuestionHandler
    - _Requisitos: 7.1, 7.2_

  - [ ]* 13.13 Escribir property tests para extracción de preguntas
    - **Property 14: Question Extraction** - Verificar extracción de texto y tipo
    - **Property 15: Question Context to AI** - Verificar envío de pregunta + CV context
    - **Valida: Requisitos 7.1, 7.2**

  - [x] 13.14 Implementar logging de preguntas y respuestas
    - Para cada pregunta respondida, loggear pregunta y respuesta
    - Formato: "Pregunta: {question} | Respuesta: {answer} | Confianza: {confidence}"
    - _Requisitos: 7.6_

  - [ ]* 13.15 Escribir property test para logging de Q&A
    - **Property 18: Question-Answer Logging** - Verificar logging de pregunta y respuesta
    - **Valida: Requisitos 7.6**

  - [x] 13.16 Implementar notas para aplicaciones inciertas
    - Si Estado = INSEGURO, agregar lista de preguntas con baja confianza a Notas
    - Formato: "Preguntas con baja confianza: {question1}, {question2}"
    - _Requisitos: 8.5_

  - [ ]* 13.17 Escribir property test para notas de aplicaciones inciertas
    - **Property 21: Uncertain Application Notes** - Verificar notas con preguntas de baja confianza
    - **Valida: Requisitos 8.5**

- [ ] 14. Checkpoint - Verificar integración completa
  - Ejecutar todos los tests de integración
  - Verificar que el flujo completo funcione end-to-end
  - Preguntar al usuario si hay dudas sobre la integración

- [ ] 15. Implementar validación pre-envío
  - [ ] 15.1 Crear función `validate_application()` en LinkedInApplier
    - Validar que todos los campos obligatorios estén rellenados
    - Validar formatos: emails contienen @, teléfonos son numéricos, URLs son válidas
    - Si respuesta single_choice no está en opciones, reducir confianza en 20% y re-evaluar
    - Si validación falla en campos críticos (email, teléfono), marcar como MANUAL
    - Logging de todas las validaciones fallidas
    - _Requisitos: 14.1, 14.2, 14.3, 14.4, 14.5_

  - [ ]* 15.2 Escribir property tests para validación
    - **Property 42: Pre-Submission Validation** - Verificar validación de campos requeridos y formatos
    - **Property 43: Invalid Option Confidence Reduction** - Verificar reducción de confianza para opciones inválidas
    - **Property 44: Critical Field Validation Failure** - Verificar marcado como MANUAL para fallos críticos
    - **Property 45: Validation Failure Logging** - Verificar logging de fallos de validación
    - **Valida: Requisitos 14.1, 14.2, 14.3, 14.4, 14.5**

  - [ ]* 15.3 Escribir unit tests para validación
    - Test de validación de campos obligatorios
    - Test de validación de formatos (email, teléfono, URL)
    - Test de reducción de confianza para opciones inválidas
    - Test de marcado como MANUAL para fallos críticos

- [x] 16. Implementar medidas anti-bot
  - [x] 16.1 Agregar delays aleatorios entre postulaciones
    - Implementar delay aleatorio entre 8-15 segundos entre trabajos
    - Usar `time.sleep(random.uniform(8, 15))`
    - _Requisitos: 12.1_

  - [ ]* 16.2 Escribir property test para delays aleatorios
    - **Property 35: Random Delays Between Applications** - Verificar delay en rango 8-15 segundos
    - **Valida: Requisitos 12.1**

  - [x] 16.3 Implementar detección de CAPTCHA y bloqueos
    - Detectar CAPTCHA buscando elementos específicos
    - Si se detecta, pausar ejecución y marcar trabajos pendientes como MANUAL
    - Detectar bloqueo de sesión verificando redirect a login
    - Guardar estado y terminar gracefully
    - _Requisitos: 12.2, 12.5_

  - [x] 16.4 Implementar persistencia de cookies de sesión
    - Cargar cookies guardadas al inicio
    - Guardar cookies al final de ejecución
    - _Requisitos: 12.3_

  - [ ]* 16.5 Escribir property test para persistencia de cookies
    - **Property 36: Session Cookie Persistence** - Verificar carga y uso de cookies guardadas
    - **Valida: Requisitos 12.3**

  - [x] 16.6 Implementar comportamiento humano simulado
    - Scroll gradual en páginas
    - Movimientos de mouse aleatorios
    - Delays variables entre acciones
    - _Requisitos: 12.4_

- [ ] 17. Implementar logging detallado y debugging
  - [ ] 17.1 Agregar logging comprehensivo
    - Loggear cada acción: carga de página, detección de modal, campos encontrados, respuestas de IA
    - Incluir timestamps y nivel de severidad (INFO, WARNING, ERROR)
    - _Requisitos: 13.1, 13.4_

  - [ ]* 17.2 Escribir property tests para logging
    - **Property 37: Comprehensive Action Logging** - Verificar logging de todas las acciones principales
    - **Property 40: Structured Log Format** - Verificar formato con timestamp y severidad
    - **Valida: Requisitos 13.1, 13.4**

  - [ ] 17.3 Implementar captura de screenshots y HTML
    - Guardar screenshot cuando campo no puede ser rellenado: data/logs/debug_*.png
    - Guardar HTML cuando modal no es detectado: data/logs/debug_html_*.html
    - _Requisitos: 13.2, 13.3_

  - [ ]* 17.4 Escribir property tests para captura de debugging
    - **Property 38: Screenshot on Field Fill Failure** - Verificar guardado de screenshot
    - **Property 39: HTML Capture on Modal Detection Failure** - Verificar guardado de HTML
    - **Valida: Requisitos 13.2, 13.3**

  - [ ] 17.5 Implementar rotación de logs
    - Rotar logs automáticamente cuando excedan 10MB
    - Formato: linkedin_applier_YYYYMMDD_HHMMSS.log
    - _Requisitos: 13.5_

  - [ ]* 17.6 Escribir property test para rotación de logs
    - **Property 41: Log Rotation** - Verificar rotación cuando archivo excede 10MB
    - **Valida: Requisitos 13.5**

- [x] 18. Implementar envío de notificación consolidada al final
  - [x] 18.1 Modificar `main()` para enviar resumen al final
    - Después de procesar todos los trabajos, llamar a `telegram_notifier.send_summary()`
    - Asegurar que se envíe exactamente una notificación
    - _Requisitos: 11.2_

  - [ ]* 18.2 Escribir unit test para envío único
    - Verificar que se llame a send_summary() exactamente una vez
    - Verificar que no se envíen notificaciones individuales

- [ ] 19. Checkpoint final - Ejecutar suite completa de tests
  - Ejecutar todos los unit tests y property tests
  - Verificar cobertura de código (mínimo 80%)
  - Verificar que todas las 49 propiedades tengan tests correspondientes
  - Preguntar al usuario si hay dudas o ajustes finales

- [ ] 20. Integración y documentación
  - [ ] 20.1 Actualizar archivo de configuración
    - Agregar variables de entorno necesarias: IA_CONFIDENCE_THRESHOLD, HIGH_THRESHOLD, LOW_THRESHOLD
    - Documentar configuración de OpenRouter API
    - _Requisitos: 8.6_

  - [ ] 20.2 Crear archivo respuestas_comunes.json
    - Agregar respuestas predefinidas para preguntas de salario
    - Formato: {"salary_expectation": "Negotiable based on role and responsibilities"}
    - _Requisitos: 9.4_

  - [ ] 20.3 Actualizar README con instrucciones de uso
    - Documentar nuevas funcionalidades
    - Explicar sistema de confianza y umbrales
    - Incluir ejemplos de configuración

## Notas

- Las tareas marcadas con `*` son opcionales (tests) y pueden omitirse para un MVP más rápido
- Cada tarea referencia requisitos específicos para trazabilidad
- Los checkpoints aseguran validación incremental
- Los property tests validan propiedades universales de corrección (49 propiedades totales)
- Los unit tests validan ejemplos específicos y casos edge
- Todos los tests deben usar mocks para dependencias externas (OpenRouter, Google Sheets, Telegram)
- Hypothesis debe configurarse con mínimo 100 iteraciones por property test
- La cobertura de código mínima es 80%
