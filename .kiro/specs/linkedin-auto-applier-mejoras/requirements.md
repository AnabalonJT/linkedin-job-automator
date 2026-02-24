# Documento de Requisitos: Mejoras al Sistema de Automatización de Postulaciones LinkedIn

## Introducción

Este documento especifica las mejoras necesarias para el sistema automatizado de postulaciones en LinkedIn. El sistema actual utiliza n8n para orquestación, Selenium para interacción web, y tiene integración con Google Sheets, Telegram y OpenRouter (IA). El problema principal es que `linkedin_applier.py` no puede interactuar correctamente con el modal de postulación que aparece después de hacer clic en "Solicitud sencilla".

## Glosario

- **Sistema_Postulador**: El módulo `linkedin_applier.py` responsable de aplicar automáticamente a trabajos
- **Modal_Postulación**: El diálogo emergente que aparece después de hacer clic en "Solicitud sencilla"
- **Clasificador_IA**: El módulo que usa OpenRouter para clasificar trabajos y responder preguntas
- **Google_Sheets**: Sistema de tracking de postulaciones
- **CV_Selector**: Componente que selecciona el CV apropiado según el trabajo
- **Formulario_Dinámico**: Los campos variables que aparecen en cada postulación
- **Nivel_Confianza**: Métrica de 0-1 que indica qué tan segura está la IA de su respuesta
- **Estado_Postulación**: Valores posibles: APPLIED, MANUAL, NO_DISPONIBLE, ERROR, INSEGURO

## Requisitos

### Requisito 1: Detección y Manejo de Trabajos No Disponibles

**User Story:** Como usuario del sistema, quiero que se detecten automáticamente los trabajos que ya no aceptan postulaciones, para mantener el tracking actualizado y no perder tiempo en ofertas cerradas.

#### Acceptance Criteria

1. WHEN THE Sistema_Postulador accede a una URL de trabajo, THE Sistema_Postulador SHALL verificar si el trabajo acepta postulaciones
2. IF el trabajo contiene indicadores de cierre (textos como "No longer accepting applications", "Ya no se aceptan solicitudes", "This job is no longer available", "Closed"), THEN THE Sistema_Postulador SHALL marcar el trabajo como "NO_DISPONIBLE" en Google_Sheets
3. WHEN un trabajo es marcado como "NO_DISPONIBLE", THE Sistema_Postulador SHALL actualizar el campo Estado con "No disponible" y agregar nota explicativa
4. THE Sistema_Postulador SHALL continuar con el siguiente trabajo sin intentar postular

### Requisito 2: Extracción de Descripciones Completas

**User Story:** Como usuario del sistema, quiero que se obtengan las descripciones completas de los trabajos incluyendo el contenido oculto detrás del botón "Ver más", para que la IA pueda tomar mejores decisiones de clasificación.

#### Acceptance Criteria

1. WHEN THE Sistema_Postulador carga una página de trabajo, THE Sistema_Postulador SHALL buscar botones de expansión (con textos "Ver más", "Show more", "See more")
2. IF existe un botón de expansión, THEN THE Sistema_Postulador SHALL hacer clic en él usando JavaScript o Selenium
3. AFTER hacer clic en expansión, THE Sistema_Postulador SHALL esperar 1-2 segundos para que el contenido cargue
4. THE Sistema_Postulador SHALL extraer el texto completo de la descripción después de la expansión
5. THE descripción completa SHALL ser pasada al Clasificador_IA para análisis

### Requisito 3: Interacción Correcta con Modal de Postulación

**User Story:** Como usuario del sistema, quiero que el sistema pueda detectar e interactuar correctamente con el modal de postulación, para completar exitosamente las aplicaciones automáticas.

#### Acceptance Criteria

1. WHEN THE Sistema_Postulador hace clic en "Solicitud sencilla", THE Sistema_Postulador SHALL esperar hasta 15 segundos a que el Modal_Postulación aparezca
2. THE Sistema_Postulador SHALL usar JavaScript para detectar el modal con selectores: `div[data-test-modal-id="easy-apply-modal"]`, `div[data-test-modal-container]`, `div.jobs-easy-apply-modal`, `div[role="dialog"]`
3. WHEN el Modal_Postulación es detectado, THE Sistema_Postulador SHALL buscar elementos del Formulario_Dinámico SOLO dentro del contexto del modal
4. THE Sistema_Postulador SHALL usar JavaScript como método primario para rellenar campos cuando Selenium falle
5. IF el modal no aparece después de 15 segundos, THEN THE Sistema_Postulador SHALL marcar el trabajo como "MANUAL" y continuar

### Requisito 4: Detección de Campos del Formulario

**User Story:** Como usuario del sistema, quiero que el sistema identifique correctamente todos los tipos de campos en el formulario, para poder rellenarlos apropiadamente.

#### Acceptance Criteria

1. THE Sistema_Postulador SHALL detectar campos de tipo: text input, email, teléfono, dropdown/select, textarea, radio buttons, checkboxes, file upload
2. WHEN busca campos, THE Sistema_Postulador SHALL usar selectores específicos del formulario de LinkedIn: `input[data-test-single-line-text-form-component]`, `select[data-test-text-entity-list-form-select]`
3. THE Sistema_Postulador SHALL identificar el propósito de cada campo usando: label asociado, placeholder, aria-label, id del elemento
4. THE Sistema_Postulador SHALL ignorar elementos fuera del Modal_Postulación (como el dropdown de idioma de LinkedIn)
5. FOR ALL campos detectados, THE Sistema_Postulador SHALL registrar en logs el tipo y propósito identificado

### Requisito 5: Selección Inteligente de CV con IA

**User Story:** Como usuario del sistema, quiero que la IA seleccione automáticamente el CV correcto basándose en el título y descripción del trabajo, para maximizar las posibilidades de éxito en la postulación.

#### Acceptance Criteria

1. WHEN THE Clasificador_IA recibe un trabajo, THE Clasificador_IA SHALL analizar el título y descripción completa del trabajo
2. THE Clasificador_IA SHALL comparar los requisitos del trabajo contra el contexto de los CVs disponibles
3. THE Clasificador_IA SHALL retornar una recomendación de CV con valores: "software" (para CV Software Engineer) o "engineer" (para CV Automatización/Data/IA)
4. THE Clasificador_IA SHALL incluir un Nivel_Confianza en la recomendación (0.0 a 1.0)
5. THE Sistema_Postulador SHALL usar el CV recomendado para la postulación
6. THE Sistema_Postulador SHALL registrar en Google_Sheets qué CV fue usado en el campo "CV_Usado"

### Requisito 6: Selección de CV por Idioma

**User Story:** Como usuario del sistema, quiero que el sistema seleccione la versión del CV en el idioma correcto (inglés o español), para cumplir con los requisitos de cada oferta.

#### Acceptance Criteria

1. THE Clasificador_IA SHALL detectar el idioma del trabajo analizando el título y descripción
2. IF el trabajo está en inglés (detectado por keywords o idioma predominante), THEN THE CV_Selector SHALL usar la versión en inglés del CV recomendado
3. IF el trabajo está en español, THEN THE CV_Selector SHALL usar la versión en español del CV recomendado
4. THE Sistema_Postulador SHALL tener acceso a 4 CVs: "CV Software Engineer Anabalon.pdf" (inglés), "CV Automatización_Data Anabalón.pdf" (español/inglés mixto), y sus contrapartes
5. THE mapping de CVs SHALL ser: software+inglés → "CV Software Engineer Anabalon.pdf", engineer+español → "CV Automatización_Data Anabalón.pdf"

### Requisito 7: Respuesta a Preguntas del Formulario con IA

**User Story:** Como usuario del sistema, quiero que la IA responda automáticamente las preguntas del formulario basándose en el contenido del CV, para completar postulaciones sin intervención manual.

#### Acceptance Criteria

1. WHEN THE Sistema_Postulador encuentra una pregunta en el Formulario_Dinámico, THE Sistema_Postulador SHALL extraer el texto de la pregunta y tipo de campo
2. THE Sistema_Postulador SHALL enviar la pregunta al Clasificador_IA junto con el contexto del CV seleccionado
3. THE Clasificador_IA SHALL analizar la pregunta y buscar información relevante en el CV
4. THE Clasificador_IA SHALL retornar una respuesta en formato JSON con campos: answer, confidence, reasoning, sources
5. THE respuesta SHALL estar en el formato apropiado según el tipo de campo (texto, número, fecha, selección)
6. FOR ALL preguntas respondidas, THE Sistema_Postulador SHALL registrar la pregunta y respuesta en logs

### Requisito 8: Sistema de Confianza para Auto-Submit

**User Story:** Como usuario del sistema, quiero que el sistema solo envíe postulaciones automáticamente cuando la IA tenga alta confianza, para evitar respuestas incorrectas que puedan perjudicar mi perfil.

#### Acceptance Criteria

1. THE Clasificador_IA SHALL calcular un Nivel_Confianza para cada respuesta (valor entre 0.0 y 1.0)
2. IF Nivel_Confianza >= 0.85, THEN THE Sistema_Postulador SHALL usar la respuesta y continuar automáticamente
3. IF Nivel_Confianza está entre 0.65 y 0.85, THEN THE Sistema_Postulador SHALL usar la respuesta pero marcar el trabajo como "INSEGURO" en Google_Sheets
4. IF Nivel_Confianza < 0.65, THEN THE Sistema_Postulador SHALL NO postular y marcar el trabajo como "MANUAL" en Google_Sheets
5. WHEN un trabajo es marcado como "INSEGURO", THE Sistema_Postulador SHALL agregar una nota en Google_Sheets indicando qué preguntas tuvieron baja confianza
6. THE umbral de confianza (0.85) SHALL ser configurable via variable de entorno IA_CONFIDENCE_THRESHOLD

### Requisito 9: Manejo de Preguntas Especiales

**User Story:** Como usuario del sistema, quiero que el sistema maneje correctamente preguntas especiales comunes (años de experiencia, elegibilidad, salario), para responder consistentemente según mi perfil.

#### Acceptance Criteria

1. WHEN THE Clasificador_IA detecta una pregunta sobre "años de experiencia" con campo numérico, THE Clasificador_IA SHALL responder SOLO con un número entero sin unidades
2. WHEN THE Clasificador_IA detecta preguntas sobre elegibilidad legal ("legally eligible", "authorized to work"), THE Clasificador_IA SHALL responder "Yes" o "Sí" con confianza >= 0.95
3. WHEN THE Clasificador_IA detecta preguntas sobre sponsorship ("require sponsorship", "need visa"), THE Clasificador_IA SHALL responder "No" con confianza >= 0.95
4. WHEN THE Clasificador_IA detecta preguntas sobre salario, THE Clasificador_IA SHALL usar respuestas configuradas en respuestas_comunes.json
5. FOR ALL preguntas de tipo number, THE Clasificador_IA SHALL validar que la respuesta sea un número válido antes de retornarla

### Requisito 10: Actualización de Google Sheets

**User Story:** Como usuario del sistema, quiero que cada postulación se registre inmediatamente en Google Sheets con toda la información relevante, para tener tracking en tiempo real.

#### Acceptance Criteria

1. WHEN THE Sistema_Postulador completa una postulación (exitosa o fallida), THE Sistema_Postulador SHALL actualizar Google_Sheets inmediatamente
2. THE registro en Google_Sheets SHALL incluir campos: ID, fecha_aplicación, Empresa, Puesto, URL, Ubicación, tipo_aplicación, CV_Usado, Estado, Último_Update, Notas
3. THE campo Estado SHALL contener uno de: "APPLIED", "MANUAL", "NO_DISPONIBLE", "ERROR", "INSEGURO"
4. IF Estado es "INSEGURO", THEN THE campo Notas SHALL incluir las preguntas que tuvieron baja confianza
5. IF Estado es "ERROR", THEN THE campo Notas SHALL incluir el mensaje de error
6. THE Sistema_Postulador SHALL manejar errores de Google Sheets gracefully sin detener el proceso de postulación

### Requisito 11: Notificaciones Telegram Consolidadas

**User Story:** Como usuario del sistema, quiero recibir un resumen consolidado por Telegram al final del proceso completo, para no ser interrumpido con notificaciones individuales.

#### Acceptance Criteria

1. THE Sistema_Postulador SHALL acumular resultados de todas las postulaciones durante la ejecución
2. WHEN el proceso completo termina, THE Sistema_Postulador SHALL enviar UNA notificación a Telegram con el resumen
3. THE notificación SHALL incluir: total de trabajos procesados, exitosas, manuales, no disponibles, errores
4. THE notificación SHALL incluir estadísticas de IA: total de preguntas respondidas, tasa de automatización, confianza promedio
5. THE notificación SHALL incluir lista de trabajos que requieren atención manual (Estado = "MANUAL" o "INSEGURO")
6. IF Telegram no está configurado, THE Sistema_Postulador SHALL continuar sin enviar notificaciones

### Requisito 12: Manejo de Errores Anti-Bot

**User Story:** Como usuario del sistema, quiero que el sistema detecte y maneje apropiadamente las medidas anti-bot de LinkedIn, para evitar bloqueos de cuenta.

#### Acceptance Criteria

1. THE Sistema_Postulador SHALL implementar delays aleatorios entre 8-15 segundos entre postulaciones
2. WHEN THE Sistema_Postulador detecta un CAPTCHA o verificación de seguridad, THE Sistema_Postulador SHALL pausar la ejecución y marcar trabajos pendientes como "MANUAL"
3. THE Sistema_Postulador SHALL usar cookies guardadas para mantener sesión entre ejecuciones
4. THE Sistema_Postulador SHALL simular comportamiento humano: scroll gradual, movimientos de mouse, delays variables
5. IF LinkedIn bloquea la sesión, THE Sistema_Postulador SHALL registrar el error y terminar gracefully sin corromper datos

### Requisito 13: Logging Detallado para Debugging

**User Story:** Como desarrollador del sistema, quiero logs detallados de cada paso del proceso, para poder diagnosticar problemas cuando las postulaciones fallen.

#### Acceptance Criteria

1. THE Sistema_Postulador SHALL registrar en logs cada acción: carga de página, detección de modal, campos encontrados, respuestas de IA
2. WHEN un campo no puede ser rellenado, THE Sistema_Postulador SHALL guardar un screenshot en data/logs/debug_*.png
3. WHEN el modal no es detectado, THE Sistema_Postulador SHALL guardar el HTML de la página en data/logs/debug_html_*.html
4. THE logs SHALL incluir timestamps y nivel de severidad (INFO, WARNING, ERROR)
5. THE Sistema_Postulador SHALL rotar logs automáticamente para evitar archivos muy grandes (máximo 10MB por archivo)

### Requisito 14: Validación de Respuestas Antes de Envío

**User Story:** Como usuario del sistema, quiero que el sistema valide las respuestas antes de enviar la postulación, para detectar errores obvios que puedan perjudicar mi aplicación.

#### Acceptance Criteria

1. WHEN THE Sistema_Postulador está listo para enviar una postulación, THE Sistema_Postulador SHALL validar que todos los campos obligatorios estén rellenados
2. THE Sistema_Postulador SHALL validar formatos: emails contienen @, teléfonos son numéricos, URLs son válidas
3. IF una respuesta de tipo "single_choice" no está en las opciones disponibles, THEN THE Sistema_Postulador SHALL reducir la confianza en 20% y re-evaluar
4. IF la validación falla en campos críticos (email, teléfono), THEN THE Sistema_Postulador SHALL marcar como "MANUAL" en lugar de enviar
5. THE Sistema_Postulador SHALL registrar en logs todas las validaciones fallidas

### Requisito 15: Recuperación de Contexto entre Ejecuciones

**User Story:** Como usuario del sistema, quiero que el sistema recuerde qué trabajos ya procesó, para no duplicar postulaciones si el proceso se interrumpe.

#### Acceptance Criteria

1. THE Sistema_Postulador SHALL mantener un archivo de estado en data/logs/application_state.json
2. WHEN inicia una ejecución, THE Sistema_Postulador SHALL cargar el estado previo y filtrar trabajos ya procesados
3. THE estado SHALL incluir: URL del trabajo, timestamp de procesamiento, resultado (APPLIED/MANUAL/ERROR)
4. IF el proceso se interrumpe, THE próxima ejecución SHALL continuar desde donde se quedó
5. THE Sistema_Postulador SHALL limpiar entradas de estado más antiguas de 30 días automáticamente

## Notas de Implementación

### Prioridad de Requisitos

- **Alta prioridad (críticos)**: Requisitos 3, 4, 5, 7, 8 - Son esenciales para que el sistema funcione
- **Media prioridad**: Requisitos 1, 2, 6, 9, 10, 11 - Mejoran significativamente la experiencia
- **Baja prioridad**: Requisitos 12, 13, 14, 15 - Son mejoras de robustez y debugging

### Consideraciones Técnicas

1. El modal de LinkedIn se carga dinámicamente con JavaScript, por lo que Selenium tradicional puede fallar. Se debe priorizar el uso de JavaScript para detección e interacción.

2. Los selectores CSS de LinkedIn pueden cambiar. Se deben usar múltiples selectores fallback y logging detallado cuando fallen.

3. OpenRouter tiene límites de rate. Se debe implementar manejo de errores 429 (rate limit) con reintentos exponenciales.

4. El contexto del CV debe ser lo suficientemente detallado para que la IA pueda responder preguntas específicas, pero no tan largo que exceda límites de tokens.

### Dependencias Externas

- OpenRouter API (para IA)
- Google Sheets API (para tracking)
- Telegram Bot API (para notificaciones)
- Selenium WebDriver (para automatización web)
- LinkedIn (plataforma objetivo - puede cambiar sin aviso)
