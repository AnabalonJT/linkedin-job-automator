# Airflow CV Upload Bugfix Design

## Overview

Este documento describe el diseño técnico para corregir 5 bugs críticos en el sistema de auto-aplicación de LinkedIn:

1. **Bug de Substring Matching en Airflow**: El sistema responde incorrectamente "2 años" para preguntas sobre Airflow debido a que el substring "ai" en "Airflow" coincide con la entrada `'ai': '2'` en el diccionario de experiencia tecnológica.

2. **Bug de Detección de Radio Buttons de CV**: El sistema no detecta los radio buttons de CV ya cargados en LinkedIn porque busca con el selector `'cv_radio': 'input[id*="jobsDocumentCardToggle"]'` dentro del modal, pero estos elementos no se encuentran.

3. **Bug de Selección de CV**: El sistema ignora la recomendación de AI para seleccionar el CV apropiado y siempre sube un nuevo archivo en lugar de seleccionar CVs ya cargados o usar la recomendación basada en job description.

4. **Bug de Expansión de Descripción**: El sistema expande correctamente la descripción del trabajo pero luego reporta error "no such element" al buscar el contenido expandido, causando un falso negativo.

5. **Bug de Logging Insuficiente**: El sistema no registra el prompt completo ni la respuesta completa del modelo AI al procesar preguntas de experiencia, dificultando el debugging.

La estrategia de corrección se basa en: (1) ordenar tecnologías por longitud descendente para priorizar coincidencias más específicas, (2) corregir el selector o la lógica de búsqueda de radio buttons, (3) implementar verificación de CVs existentes antes de subir nuevos, (4) usar selectores correctos después de la expansión, y (5) agregar logging completo de interacciones con AI.

## Glossary

- **Bug_Condition (C)**: Las condiciones que activan cada uno de los 5 bugs
- **Property (P)**: El comportamiento deseado cuando se corrigen los bugs
- **Preservation**: Comportamientos existentes que deben permanecer sin cambios
- **tech_experience**: Diccionario en `QuestionHandler._handle_experience_question` que mapea tecnologías a años de experiencia
- **substring matching**: Búsqueda de coincidencias parciales en strings que causa el bug de Airflow
- **cv_radio**: Tipo de campo para radio buttons de selección de CV en `FormFieldDetector.FIELD_TYPES`
- **handle_cv_upload**: Función en `linkedin_applier.py` que maneja la subida de CV
- **select_cv_by_keywords**: Función en `cv_selector.py` que usa AI para recomendar el CV apropiado
- **expandable-text-button**: Selector del botón para expandir descripciones de trabajo en LinkedIn

## Bug Details

### Bug 1: Airflow Substring Matching

#### Fault Condition

El bug se manifiesta cuando una pregunta contiene "Airflow" (o cualquier tecnología que contenga "ai" como substring). El método `_handle_experience_question` itera sobre el diccionario `tech_experience` y verifica si cada clave está contenida en `question_lower` usando `if tech in question_lower`. Como Python itera sobre diccionarios en orden de inserción (Python 3.7+), cuando encuentra `'ai': '2'` antes de `'airflow': '0'`, el substring "ai" coincide con "Airflow" y retorna "2" años incorrectamente.

**Formal Specification:**
```
FUNCTION isBugCondition_Airflow(input)
  INPUT: input of type (question: str, question_lower: str)
  OUTPUT: boolean
  
  RETURN ('airflow' IN question_lower OR 'Airflow' IN input.question)
         AND tech_experience dictionary contains 'ai' before 'airflow'
         AND 'ai' is substring of 'airflow'
         AND function returns '2' instead of '0'
END FUNCTION
```

#### Examples

- **Input**: "¿Cuántos años de experiencia tienes en Airflow?"
  - **Expected**: answer="0", reasoning="NO tengo experiencia con Airflow según CV"
  - **Actual**: answer="2", reasoning="Años de experiencia con ai según CV"

- **Input**: "How many years of experience do you have with Apache Airflow?"
  - **Expected**: answer="0", reasoning="NO tengo experiencia con Airflow según CV"
  - **Actual**: answer="2", reasoning="Años de experiencia con ai según CV"

- **Input**: "Do you have Airflow experience?"
  - **Expected**: answer="0" (for numeric fields) or "No" (for text fields)
  - **Actual**: answer="2"

### Bug 2: CV Radio Button Detection Failure

#### Fault Condition

El bug se manifiesta cuando el sistema procesa el paso 2 del formulario que contiene radio buttons para seleccionar CVs ya cargados. El selector `'cv_radio': 'input[id*="jobsDocumentCardToggle"]'` en `FormFieldDetector.FIELD_TYPES` no encuentra los elementos, resultando en 0 campos detectados. Esto puede deberse a: (1) el selector es incorrecto, (2) los elementos no están presentes en el momento de la búsqueda, o (3) los elementos están fuera del contexto del modal.

**Formal Specification:**
```
FUNCTION isBugCondition_CVRadio(input)
  INPUT: input of type (modal_element: WebElement, step: int)
  OUTPUT: boolean
  
  RETURN step == 2
         AND LinkedIn has pre-uploaded CVs
         AND modal_element.find_elements("css selector", 'input[id*="jobsDocumentCardToggle"]') returns []
         AND actual CV radio buttons exist in DOM
END FUNCTION
```

#### Examples

- **Scenario**: Usuario tiene 2 CVs pre-cargados en LinkedIn
  - **Expected**: `detect_fields()` retorna 2 FormField con field_type='cv_radio'
  - **Actual**: `detect_fields()` retorna 0 campos, log muestra "Total de campos detectados: 0"

- **Scenario**: Usuario tiene 1 CV pre-cargado y el formulario muestra radio button
  - **Expected**: Sistema detecta el radio button y lo selecciona si coincide con recomendación
  - **Actual**: Sistema no detecta el radio button, intenta subir nuevo CV con `input[type='file']`

### Bug 3: CV Selection Ignoring AI Recommendation

#### Fault Condition

El bug se manifiesta cuando el sistema llama `handle_cv_upload()` después de abrir el modal. La función siempre busca `input[type='file']` y sube un nuevo archivo, ignorando: (1) si ya hay CVs disponibles para seleccionar (radio buttons), y (2) la recomendación de AI de `select_cv_by_keywords()` basada en job title y description. El flujo correcto debería ser: verificar CVs existentes → obtener recomendación AI → seleccionar radio button del CV recomendado → solo si no hay CVs, subir nuevo archivo.

**Formal Specification:**
```
FUNCTION isBugCondition_CVSelection(input)
  INPUT: input of type (modal_state: ModalState, job: Dict)
  OUTPUT: boolean
  
  RETURN modal_state.has_preloaded_cvs == True
         AND modal_state.cv_radio_buttons.length > 0
         AND system calls handle_cv_upload()
         AND handle_cv_upload() searches for input[type='file'] first
         AND handle_cv_upload() does NOT call select_cv_by_keywords(job.title, job.description)
         AND system uploads new file instead of selecting existing CV
END FUNCTION
```

#### Examples

- **Scenario**: LinkedIn tiene 2 CVs pre-cargados: "CV Software Engineer.pdf" y "CV Automatización Data.pdf"
  - Job title: "Data Engineer"
  - **Expected**: Sistema llama `select_cv_by_keywords("Data Engineer", description)` → recomienda "engineer" → selecciona radio button de "CV Automatización Data.pdf"
  - **Actual**: Sistema busca `input[type='file']`, sube nuevo archivo ignorando CVs existentes

- **Scenario**: LinkedIn tiene 1 CV pre-cargado que coincide con la recomendación
  - **Expected**: Sistema selecciona el radio button del CV existente
  - **Actual**: Sistema sube un nuevo archivo duplicado

- **Scenario**: Job description menciona "Python, Django, REST APIs"
  - **Expected**: AI recomienda cv_type="software", sistema usa ese CV
  - **Actual**: Sistema usa CV predeterminado sin consultar AI

### Bug 4: Job Description Expansion False Negative

#### Fault Condition

El bug se manifiesta cuando el sistema expande la descripción del trabajo haciendo clic en `button[data-testid='expandable-text-button']`. El contenido se expande correctamente en el DOM, pero inmediatamente después el sistema busca el contenido con selectores `.jobs-description__content, .jobs-description` y no lo encuentra, reportando error "no such element". Esto causa un falso negativo: el sistema cree que falló la expansión cuando en realidad fue exitosa, pero los selectores usados después de la expansión son incorrectos o el contenido tarda en renderizarse.

**Formal Specification:**
```
FUNCTION isBugCondition_DescriptionExpansion(input)
  INPUT: input of type (expand_button: WebElement, description_selectors: List[str])
  OUTPUT: boolean
  
  RETURN expand_button.click() succeeds
         AND DOM content is expanded (visible in browser)
         AND for all selector in description_selectors:
             driver.find_element(selector) raises NoSuchElementException
         AND system reports "no such element" error
         AND system treats expansion as failed (false negative)
END FUNCTION
```

#### Examples

- **Scenario**: Job description tiene botón "Ver más"
  - **Expected**: Sistema hace clic → espera renderizado → encuentra contenido con selector correcto → extrae descripción completa
  - **Actual**: Sistema hace clic → contenido se expande → busca inmediatamente con `.jobs-description__content` → no encuentra → reporta error

- **Scenario**: Descripción se expande pero el selector cambia después de expansión
  - **Expected**: Sistema usa selector que funciona post-expansión
  - **Actual**: Sistema usa selector pre-expansión que ya no existe, falla

- **Scenario**: Contenido tarda 1-2 segundos en renderizarse después del clic
  - **Expected**: Sistema espera suficiente tiempo antes de buscar
  - **Actual**: Sistema busca inmediatamente, no encuentra, reporta error

### Bug 5: Insufficient Logging for AI Interactions

#### Fault Condition

El bug se manifiesta cuando el sistema procesa preguntas de experiencia usando `_handle_experience_question` o llama a OpenRouter API en `answer_question`. El sistema no registra en el log: (1) el prompt completo enviado a la API, (2) la respuesta completa recibida del modelo, (3) el JSON parseado antes de extraer campos. Esto dificulta el debugging cuando las respuestas son incorrectas, ya que no se puede ver qué información recibió el modelo ni qué respondió exactamente.

**Formal Specification:**
```
FUNCTION isBugCondition_InsufficientLogging(input)
  INPUT: input of type (question: str, api_call: bool)
  OUTPUT: boolean
  
  RETURN (question matches experience pattern AND _handle_experience_question is called)
         OR (answer_question calls OpenRouter API)
         AND log does NOT contain full system_prompt
         AND log does NOT contain full user_message
         AND log does NOT contain full API response
         AND log does NOT contain parsed JSON before field extraction
END FUNCTION
```

#### Examples

- **Scenario**: Pregunta "¿Cuántos años de experiencia tienes en Airflow?"
  - **Expected**: Log muestra: prompt completo → respuesta API completa → JSON parseado → answer="0", confidence=0.95
  - **Actual**: Log solo muestra: "Respondiendo pregunta: ¿Cuántos años..." y "Respuesta IA: 2 (confianza: 0.95)"

- **Scenario**: AI responde con JSON inválido o con campos inesperados
  - **Expected**: Log muestra el JSON completo recibido para debugging
  - **Actual**: Log solo muestra error genérico "Error al responder pregunta con IA"

- **Scenario**: Debugging por qué AI respondió "2" en lugar de "0" para Airflow
  - **Expected**: Log muestra el reasoning completo del modelo: "Años de experiencia con ai según CV"
  - **Actual**: Log no muestra el reasoning, solo el answer final

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Preguntas sobre tecnologías con experiencia real (Python, SQL, AWS, Ruby) deben continuar respondiendo con los años correctos según cv_context.json
- Ordenamiento por longitud descendente para tecnologías con nombres largos (machine learning, apache airflow) debe continuar funcionando
- Detección de otros tipos de campos (text, numeric, email, phone, dropdown, textarea) debe continuar funcionando correctamente
- Procesamiento de pasos del formulario que no contienen campos de CV debe continuar normalmente
- Preguntas sobre tecnologías con 0 años de experiencia (kubernetes, spark, kafka) deben continuar respondiendo "0"
- Cuando no hay CVs pre-cargados y solo existe `input[type='file']`, el sistema debe continuar subiendo el CV apropiado
- Llenado de campos de texto, email, teléfono, y dropdowns debe continuar usando valores correctos
- Procesamiento de descripciones sin botón de expandir debe continuar sin errores

**Scope:**
Todas las entradas que NO involucran los 5 bugs específicos deben ser completamente no afectadas por este fix. Esto incluye:
- Preguntas sobre tecnologías que no contienen substrings problemáticos
- Formularios sin campos de CV
- Descripciones de trabajo que no requieren expansión
- Todas las demás interacciones con AI que no sean preguntas de experiencia

## Hypothesized Root Cause

### Bug 1: Airflow Substring Matching

**Root Cause**: Orden de iteración del diccionario y búsqueda de substring sin priorización

El diccionario `tech_experience` contiene:
```python
tech_experience = {
    'python': '5',
    'ruby': '3',
    # ...
    'ai': '2',
    # ...
    'airflow': '0'  # Nunca se alcanza porque 'ai' coincide primero
}
```

El código itera con `for tech, years in tech_experience.items()` y verifica `if tech in question_lower`. Cuando la pregunta contiene "airflow":
1. Itera sobre 'python' → no coincide
2. Itera sobre 'ruby' → no coincide
3. Itera sobre 'ai' → **coincide** (porque "ai" está en "airflow") → retorna "2"
4. Nunca llega a verificar 'airflow' → nunca retorna "0"

**Solución**: Ordenar las claves del diccionario por longitud descendente antes de iterar, para que coincidencias más específicas (como "airflow") se verifiquen antes que substrings genéricos (como "ai").

### Bug 2: CV Radio Button Detection Failure

**Root Cause**: Selector incorrecto o timing de búsqueda

Posibles causas:
1. **Selector incorrecto**: El selector `'input[id*="jobsDocumentCardToggle"]'` no coincide con el atributo `id` real de los radio buttons en el DOM de LinkedIn
2. **Timing issue**: Los radio buttons se renderizan después de que `detect_fields()` ejecuta la búsqueda
3. **Contexto incorrecto**: Los radio buttons están fuera del `modal_element` usado como contexto de búsqueda
4. **Estructura DOM diferente**: LinkedIn cambió la estructura y los radio buttons ahora usan diferentes atributos o clases

**Solución**: Inspeccionar el DOM real de LinkedIn cuando hay CVs pre-cargados, identificar el selector correcto, y posiblemente agregar espera explícita para que los elementos se rendericen.

### Bug 3: CV Selection Ignoring AI Recommendation

**Root Cause**: Lógica de flujo incorrecta en `handle_cv_upload()`

La función `handle_cv_upload()` tiene este flujo:
```python
def handle_cv_upload(self, job, result, search_context):
    # Busca input[type='file'] inmediatamente
    file_inputs = self.find_elements_in_context(search_context, By.CSS_SELECTOR, "input[type='file']")
    
    if not file_inputs:
        return True  # Asume que no hay upload necesario
    
    # Selecciona CV usando función antigua (no usa AI)
    cv_type = select_cv_by_keywords(job.get('title', ''), job.get('description', ''), self.config)
    
    # Sube archivo directamente
    file_inputs[0].send_keys(str(Path(cv_path).absolute()))
```

Problemas:
1. No verifica si existen radio buttons de CVs pre-cargados antes de buscar `input[type='file']`
2. Aunque llama `select_cv_by_keywords()`, no usa la recomendación para seleccionar entre CVs existentes
3. Siempre sube un nuevo archivo si encuentra `input[type='file']`, incluso si hay CVs disponibles

**Solución**: Refactorizar el flujo para: (1) verificar CVs existentes primero, (2) obtener recomendación AI, (3) intentar seleccionar CV existente que coincida, (4) solo si no hay coincidencia, subir nuevo archivo.

### Bug 4: Job Description Expansion False Negative

**Root Cause**: Selectores incorrectos post-expansión o timing insuficiente

Después de hacer clic en el botón de expansión, el código busca inmediatamente:
```python
description_selectors = [
    ".jobs-description__content",
    ".jobs-description",
    # ...
]

for desc_selector in description_selectors:
    description_element = self.driver.find_element(By.CSS_SELECTOR, desc_selector)
```

Problemas:
1. **Timing**: El contenido expandido puede tardar 1-2 segundos en renderizarse completamente
2. **Selectores obsoletos**: Los selectores pueden cambiar después de la expansión (LinkedIn puede reemplazar el DOM)
3. **Falta de espera explícita**: No hay `WebDriverWait` para esperar que el contenido expandido esté presente

**Solución**: Agregar espera explícita con `WebDriverWait` después del clic, y verificar selectores correctos que funcionen post-expansión.

### Bug 5: Insufficient Logging for AI Interactions

**Root Cause**: Falta de statements de logging en puntos críticos

El código actual solo registra:
```python
logger.info(f"Respondiendo pregunta: {question} (tipo: {field_type})")
# ... llamada a API ...
logger.info(f"Respuesta IA: {answer} (confianza: {confidence:.2f})")
```

Falta logging de:
1. Prompt completo (`system_prompt` + `user_message`) antes de enviar a API
2. Respuesta raw completa de la API antes de parsear
3. JSON parseado con todos los campos antes de extraer `answer`, `confidence`, `reasoning`
4. Reasoning completo del modelo para entender decisiones

**Solución**: Agregar statements de logging en cada paso del flujo de AI, especialmente antes y después de llamadas a API.

## Correctness Properties

Property 1: Fault Condition - Airflow Experience Returns Zero

_For any_ question input where "airflow" (case-insensitive) is mentioned and the tech_experience dictionary contains both 'ai' and 'airflow' entries, the fixed `_handle_experience_question` function SHALL return answer="0" with reasoning indicating no Airflow experience, by checking longer/more specific technology names before shorter substring matches.

**Validates: Requirements 2.1, 2.2**

Property 2: Fault Condition - CV Radio Buttons Detected

_For any_ modal state where LinkedIn has pre-uploaded CVs with radio buttons in the DOM, the fixed `detect_fields` function SHALL detect and return FormField objects with field_type='cv_radio' for each available CV, using correct selectors and timing.

**Validates: Requirements 2.3, 2.4**

Property 3: Fault Condition - CV Selection Uses AI Recommendation

_For any_ job application where the modal contains CV upload fields, the fixed `handle_cv_upload` function SHALL first check for existing CVs (radio buttons), call `select_cv_by_keywords()` with job title and description to get AI recommendation, attempt to select the recommended CV from existing options, and only upload a new file if no matching CV exists.

**Validates: Requirements 2.5, 2.6, 2.7**

Property 4: Fault Condition - Job Description Expansion Succeeds

_For any_ job description with an expandable content button, the fixed expansion logic SHALL click the button, wait for content to render using explicit waits, use correct post-expansion selectors to find the content, and successfully extract the full description without false negative errors.

**Validates: Requirements 2.8**

Property 5: Fault Condition - AI Interactions Fully Logged

_For any_ question processed by `_handle_experience_question` or `answer_question` that involves OpenRouter API calls, the fixed logging SHALL record the complete system prompt, complete user message, complete API response, and parsed JSON with all fields before extraction.

**Validates: Requirements 2.9**

Property 6: Preservation - Existing Technology Experience Responses

_For any_ question about technologies with real experience (Python, SQL, AWS, Ruby, etc.) where the bug condition does NOT hold (not affected by substring matching), the fixed function SHALL produce exactly the same answer and confidence as the original function, preserving correct responses for all non-buggy technology queries.

**Validates: Requirements 3.1, 3.2, 3.5**

Property 7: Preservation - Other Field Detection

_For any_ form field that is NOT a CV radio button (text, numeric, email, phone, dropdown, textarea, file), the fixed `detect_fields` function SHALL produce exactly the same detection results as the original function, preserving all existing field detection logic.

**Validates: Requirements 3.3, 3.4**

Property 8: Preservation - CV Upload When No Pre-loaded CVs

_For any_ application form where LinkedIn does NOT have pre-loaded CVs and only `input[type='file']` exists, the fixed `handle_cv_upload` function SHALL produce exactly the same behavior as the original function, uploading the appropriate CV file using `send_keys()`.

**Validates: Requirements 3.6, 3.7**

Property 9: Preservation - Non-expandable Descriptions

_For any_ job description that does NOT have an expandable content button, the fixed description extraction logic SHALL produce exactly the same behavior as the original function, processing the visible description without errors.

**Validates: Requirements 3.8**

## Fix Implementation

### Changes Required

Asumiendo que nuestro análisis de causa raíz es correcto:

#### Bug 1: Airflow Substring Matching

**File**: `scripts/question_handler.py`

**Function**: `_handle_experience_question`

**Specific Changes**:
1. **Ordenar tecnologías por longitud**: Antes de iterar sobre `tech_experience.items()`, ordenar las claves por longitud descendente
   ```python
   # Ordenar tecnologías por longitud (más largas primero) para evitar substring matching incorrecto
   sorted_techs = sorted(tech_experience.items(), key=lambda x: len(x[0]), reverse=True)
   
   for tech, years in sorted_techs:
       if tech in question_lower:
           return QuestionAnswer(...)
   ```

2. **Agregar entrada explícita para Airflow**: Asegurar que el diccionario `tech_experience` tenga entrada explícita para 'airflow' con valor '0'
   ```python
   tech_experience = {
       'python': '5',
       'ruby': '3',
       # ... otras tecnologías ...
       'airflow': '0',  # Explícitamente 0 años
       'kubernetes': '0',
       'spark': '0',
       'kafka': '0',
       # ... continuar con el resto
   }
   ```

3. **Considerar coincidencias exactas de palabras**: Opcionalmente, usar word boundaries para evitar substring matching
   ```python
   import re
   # Verificar coincidencia de palabra completa primero
   if re.search(rf'\b{re.escape(tech)}\b', question_lower, re.IGNORECASE):
       return QuestionAnswer(...)
   ```

#### Bug 2: CV Radio Button Detection Failure

**File**: `scripts/form_field_detector.py`

**Class**: `FormFieldDetector`

**Specific Changes**:
1. **Inspeccionar y corregir selector**: Verificar el DOM real de LinkedIn y actualizar el selector en `FIELD_TYPES`
   ```python
   FIELD_TYPES = {
       # ... otros tipos ...
       'cv_radio': 'input[type="radio"][id*="document"], input[type="radio"][name*="document"], label.jobs-document-upload-redesign-card__container input[type="radio"]'
   }
   ```

2. **Agregar espera explícita**: En `detect_fields()`, agregar espera para que los radio buttons se rendericen
   ```python
   from selenium.webdriver.support.ui import WebDriverWait
   from selenium.webdriver.support import expected_conditions as EC
   
   # Esperar a que los radio buttons estén presentes
   try:
       WebDriverWait(modal_element, 5).until(
           EC.presence_of_element_located((By.CSS_SELECTOR, selector))
       )
   except TimeoutException:
       logger.debug(f"Timeout esperando elementos {field_type}")
   ```

3. **Buscar en contexto más amplio**: Si los radio buttons están fuera del modal, buscar en un contexto padre
   ```python
   # Intentar buscar en modal primero, luego en contexto más amplio
   elements = modal_element.find_elements("css selector", selector)
   if not elements and field_type == 'cv_radio':
       # Intentar buscar en toda la página
       elements = modal_element.find_elements("xpath", "//input[@type='radio' and contains(@id, 'document')]")
   ```

4. **Logging detallado**: Agregar logging cuando no se encuentran radio buttons esperados
   ```python
   if field_type == 'cv_radio' and not elements:
       logger.warning(f"No se encontraron radio buttons de CV con selector: {selector}")
       logger.warning(f"HTML del modal: {modal_element.get_attribute('outerHTML')[:500]}")
   ```

#### Bug 3: CV Selection Ignoring AI Recommendation

**File**: `scripts/linkedin_applier.py`

**Function**: `handle_cv_upload`

**Specific Changes**:
1. **Verificar CVs existentes primero**: Antes de buscar `input[type='file']`, verificar si hay radio buttons
   ```python
   def handle_cv_upload(self, job, result, search_context):
       # 1. Obtener recomendación de AI primero
       cv_recommendation = self.cv_selector.select_cv(
           job.get('title', ''),
           job.get('description', '')
       )
       logger.info(f"Recomendación AI: {cv_recommendation.cv_type} ({cv_recommendation.language})")
       
       # 2. Buscar radio buttons de CVs existentes
       cv_radios = self.find_elements_in_context(
           search_context, 
           By.CSS_SELECTOR, 
           "input[type='radio'][id*='document']"
       )
       
       if cv_radios:
           logger.info(f"Encontrados {len(cv_radios)} CVs pre-cargados")
           # Intentar seleccionar el CV recomendado
           for radio in cv_radios:
               if self._matches_recommendation(radio, cv_recommendation):
                   radio.click()
                   logger.info(f"CV seleccionado: {cv_recommendation.cv_type}")
                   return True
       
       # 3. Si no hay CVs existentes o no coinciden, subir nuevo
       file_inputs = self.find_elements_in_context(search_context, By.CSS_SELECTOR, "input[type='file']")
       if file_inputs:
           cv_path = cv_recommendation.cv_path
           file_inputs[0].send_keys(str(Path(cv_path).absolute()))
           logger.info(f"CV subido: {cv_path}")
           return True
       
       return False
   ```

2. **Implementar función de matching**: Crear función auxiliar para verificar si un radio button coincide con la recomendación
   ```python
   def _matches_recommendation(self, radio_element, cv_recommendation):
       """Verifica si un radio button de CV coincide con la recomendación de AI"""
       try:
           # Obtener el label o nombre del archivo asociado
           parent = radio_element.find_element(By.XPATH, "../..")
           file_name = parent.find_element(By.CSS_SELECTOR, ".jobs-document-upload-redesign-card__file-name").text
           
           # Verificar si el nombre contiene keywords del tipo de CV recomendado
           cv_keywords = {
               'software': ['software', 'engineer', 'backend', 'fullstack'],
               'engineer': ['automatización', 'automation', 'data', 'ml', 'ai']
           }
           
           keywords = cv_keywords.get(cv_recommendation.cv_type, [])
           return any(keyword.lower() in file_name.lower() for keyword in keywords)
       except Exception as e:
           logger.debug(f"Error verificando match de CV: {e}")
           return False
   ```

3. **Usar CVSelector existente**: Asegurar que se usa la instancia de `CVSelector` con AI
   ```python
   # En __init__ de LinkedInApplier
   self.cv_selector = CVSelector(api_key=self.config.get('openrouter_api_key'))
   ```

#### Bug 4: Job Description Expansion False Negative

**File**: `scripts/linkedin_applier.py`

**Function**: `get_job_description` (método que expande descripciones)

**Specific Changes**:
1. **Agregar espera explícita después del clic**: Usar `WebDriverWait` para esperar que el contenido expandido esté presente
   ```python
   from selenium.webdriver.support.ui import WebDriverWait
   from selenium.webdriver.support import expected_conditions as EC
   
   # Después de hacer clic en el botón de expansión
   self.driver.execute_script("arguments[0].click();", expand_button)
   logger.info(f"✓ Botón de expansión clickeado: {selector}")
   
   # Esperar a que el contenido expandido esté presente
   try:
       WebDriverWait(self.driver, 5).until(
           EC.presence_of_element_located((By.CSS_SELECTOR, ".jobs-description__content"))
       )
       logger.info("✓ Contenido expandido renderizado")
   except TimeoutException:
       logger.warning("Timeout esperando contenido expandido, continuando...")
   
   time.sleep(1)  # Espera adicional para asegurar renderizado completo
   ```

2. **Actualizar selectores post-expansión**: Verificar qué selectores funcionan después de la expansión
   ```python
   # Selectores que funcionan después de expansión
   description_selectors = [
       "div.jobs-description__content",  # Selector más específico
       "div[class*='jobs-description__content']",
       "article.jobs-description",
       "div.jobs-box__html-content",
       "section.jobs-description",  # Selector alternativo
   ]
   ```

3. **Mejorar manejo de errores**: No reportar error si el contenido se expandió exitosamente
   ```python
   # Después de intentar todos los selectores
   if not full_description:
       # Verificar si el botón de expansión ya no está visible (señal de que se expandió)
       try:
           expand_button = self.driver.find_element(By.CSS_SELECTOR, "button[data-testid='expandable-text-button']")
           if not expand_button.is_displayed():
               logger.info("✓ Contenido parece estar expandido (botón no visible)")
               # Intentar extraer con selector más general
               full_description = self.driver.find_element(By.TAG_NAME, "body").text
       except NoSuchElementException:
           logger.info("✓ Botón de expansión no encontrado (ya expandido)")
   ```

4. **Logging más detallado**: Registrar éxito/fallo de cada paso
   ```python
   logger.info(f"Intentando expandir descripción...")
   logger.info(f"Botón encontrado: {selector}")
   logger.info(f"Clic ejecutado, esperando renderizado...")
   logger.info(f"Buscando contenido con {len(description_selectors)} selectores...")
   logger.info(f"✓ Descripción extraída: {len(full_description)} caracteres")
   ```

#### Bug 5: Insufficient Logging for AI Interactions

**File**: `scripts/question_handler.py`

**Function**: `answer_question` y `_handle_experience_question`

**Specific Changes**:
1. **Logging de prompts completos**: Antes de llamar a la API
   ```python
   # En answer_question(), antes de self.client.call()
   logger.info("=" * 80)
   logger.info("LLAMADA A OPENROUTER API")
   logger.info("=" * 80)
   logger.info(f"SYSTEM PROMPT:\n{system_prompt}")
   logger.info("-" * 80)
   logger.info(f"USER MESSAGE:\n{user_message}")
   logger.info("=" * 80)
   
   response = self.client.call(...)
   ```

2. **Logging de respuestas completas**: Después de recibir respuesta de API
   ```python
   # Después de self.client.call()
   logger.info("=" * 80)
   logger.info("RESPUESTA DE OPENROUTER API")
   logger.info("=" * 80)
   logger.info(f"RAW RESPONSE:\n{response}")
   logger.info("=" * 80)
   
   result = self.client.extract_json_response(response)
   
   logger.info("JSON PARSEADO:")
   logger.info(json.dumps(result, indent=2, ensure_ascii=False))
   logger.info("=" * 80)
   ```

3. **Logging de reasoning completo**: Extraer y registrar el reasoning del modelo
   ```python
   reasoning = result.get('reasoning', 'Respuesta generada por IA')
   logger.info(f"REASONING DEL MODELO: {reasoning}")
   logger.info(f"CONFIDENCE: {confidence}")
   logger.info(f"ANSWER: {answer}")
   ```

4. **Logging en _handle_experience_question**: Registrar qué tecnología coincidió
   ```python
   def _handle_experience_question(self, question, question_lower, field_type):
       logger.info(f"Procesando pregunta de experiencia: {question}")
       
       # Ordenar tecnologías
       sorted_techs = sorted(tech_experience.items(), key=lambda x: len(x[0]), reverse=True)
       logger.debug(f"Tecnologías ordenadas: {[tech for tech, _ in sorted_techs[:5]]}...")
       
       for tech, years in sorted_techs:
           if tech in question_lower:
               logger.info(f"✓ COINCIDENCIA ENCONTRADA: '{tech}' → {years} años")
               logger.info(f"  Pregunta contenía: '{tech}' en '{question_lower}'")
               return QuestionAnswer(
                   question=question,
                   answer=years,
                   confidence=0.95,
                   reasoning=f"Años de experiencia con {tech} según CV",
                   sources=["Experiencia profesional"],
                   field_type=field_type
               )
       
       logger.info("No se encontró tecnología específica, usando experiencia general")
       return QuestionAnswer(...)
   ```

5. **Configurar nivel de logging**: Asegurar que el logger está configurado para mostrar INFO
   ```python
   # En __init__ o al inicio del módulo
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   ```

## Testing Strategy

### Validation Approach

La estrategia de testing sigue un enfoque de dos fases: primero, surface counterexamples que demuestren los bugs en el código sin corregir, luego verificar que el fix funciona correctamente y preserva el comportamiento existente. Dado que hay 5 bugs independientes, cada uno requiere su propia estrategia de exploratory checking, fix checking, y preservation checking.

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples que demuestren los 5 bugs ANTES de implementar el fix. Confirmar o refutar el análisis de causa raíz. Si refutamos, necesitaremos re-hipotetizar.

#### Bug 1: Airflow Substring Matching

**Test Plan**: Escribir tests que llamen `_handle_experience_question` con preguntas sobre Airflow y verificar que la respuesta es "2" (incorrecta) en el código sin corregir.

**Test Cases**:
1. **Airflow Spanish Question**: Pregunta "¿Cuántos años de experiencia tienes en Airflow?" → esperamos answer="2" (bug) en unfixed code
2. **Airflow English Question**: Pregunta "How many years of experience do you have with Apache Airflow?" → esperamos answer="2" (bug) en unfixed code
3. **Airflow Substring Test**: Verificar que "ai" en "airflow" causa la coincidencia incorrecta → esperamos que el loop retorne en 'ai' antes de llegar a 'airflow'
4. **Other Substring Bugs**: Probar otras tecnologías que puedan tener substring issues (ej: "spark" contiene "par", "kafka" contiene "ka")

**Expected Counterexamples**:
- `_handle_experience_question("¿Cuántos años de experiencia tienes en Airflow?", "¿cuántos años de experiencia tienes en airflow?", "number")` retorna answer="2" con reasoning="Años de experiencia con ai según CV"
- El loop itera sobre 'ai' antes de 'airflow' y retorna prematuramente

#### Bug 2: CV Radio Button Detection Failure

**Test Plan**: Crear un mock de modal HTML con radio buttons de CV y verificar que `detect_fields()` retorna 0 campos (bug) en unfixed code.

**Test Cases**:
1. **Mock LinkedIn CV Radio Buttons**: Crear HTML con estructura similar a LinkedIn con `<input type="radio" id="jobsDocumentCardToggle-123">` → esperamos 0 campos detectados (bug)
2. **Alternative Selector Test**: Probar selectores alternativos para ver cuál funciona → esperamos que el selector actual falle
3. **Timing Test**: Verificar si agregar espera antes de `detect_fields()` ayuda → esperamos que timing no sea el problema si el selector es incorrecto
4. **Context Test**: Verificar si los radio buttons están dentro o fuera del modal → esperamos encontrarlos fuera si el contexto es el problema

**Expected Counterexamples**:
- `detect_fields(modal_element)` con modal que contiene radio buttons retorna lista vacía `[]`
- `modal_element.find_elements("css selector", 'input[id*="jobsDocumentCardToggle"]')` retorna `[]` incluso cuando los elementos existen en el DOM

#### Bug 3: CV Selection Ignoring AI Recommendation

**Test Plan**: Mockear un escenario con CVs pre-cargados y verificar que `handle_cv_upload()` sube un nuevo archivo en lugar de seleccionar el existente (bug) en unfixed code.

**Test Cases**:
1. **Pre-loaded CVs Ignored**: Modal con 2 radio buttons de CV → esperamos que `handle_cv_upload()` busque `input[type='file']` y suba nuevo archivo (bug)
2. **AI Recommendation Not Used**: Job con title="Data Engineer" → esperamos que no se llame `select_cv_by_keywords()` o que su resultado sea ignorado (bug)
3. **Flow Analysis**: Verificar el orden de ejecución → esperamos que busque file input antes de verificar radio buttons (bug)
4. **CVSelector Not Instantiated**: Verificar si `self.cv_selector` existe → esperamos que no esté inicializado o no se use (bug)

**Expected Counterexamples**:
- `handle_cv_upload()` con modal que tiene radio buttons ejecuta `find_elements("input[type='file']")` primero
- No se llama `self.cv_selector.select_cv()` o su resultado no se usa para seleccionar radio buttons
- Siempre se sube un nuevo archivo incluso cuando hay CVs disponibles

#### Bug 4: Job Description Expansion False Negative

**Test Plan**: Mockear un escenario donde el botón de expansión existe y se hace clic, pero la búsqueda de contenido falla (bug) en unfixed code.

**Test Cases**:
1. **Expansion Click Success, Content Search Fails**: Botón existe y se hace clic → contenido se expande en DOM → búsqueda con `.jobs-description__content` falla → esperamos error "no such element" (bug)
2. **Timing Issue**: Verificar si agregar sleep después del clic ayuda → esperamos que no sea suficiente si los selectores son incorrectos (bug)
3. **Selector Change Post-Expansion**: Verificar si los selectores cambian después de expansión → esperamos que los selectores pre-expansión no funcionen post-expansión (bug)
4. **False Negative Reporting**: Verificar que el sistema reporta error incluso cuando la expansión fue exitosa → esperamos log de error a pesar de éxito visual (bug)

**Expected Counterexamples**:
- Clic en botón de expansión ejecuta exitosamente, pero `find_element(".jobs-description__content")` lanza `NoSuchElementException`
- Log muestra "✓ Descripción expandida" seguido de "Error: no such element"
- Contenido está visible en el browser pero el código no puede encontrarlo

#### Bug 5: Insufficient Logging for AI Interactions

**Test Plan**: Ejecutar `answer_question()` con una pregunta y verificar que el log NO contiene el prompt completo ni la respuesta completa (bug) en unfixed code.

**Test Cases**:
1. **Missing System Prompt**: Llamar `answer_question()` → verificar log → esperamos que NO contenga el system_prompt completo (bug)
2. **Missing User Message**: Verificar log → esperamos que NO contenga el user_message completo (bug)
3. **Missing API Response**: Verificar log → esperamos que NO contenga la respuesta raw de la API (bug)
4. **Missing Parsed JSON**: Verificar log → esperamos que NO contenga el JSON parseado antes de extraer campos (bug)
5. **Missing Reasoning**: Verificar log → esperamos que NO contenga el reasoning completo del modelo (bug)

**Expected Counterexamples**:
- Log solo contiene: "Respondiendo pregunta: ..." y "Respuesta IA: ... (confianza: ...)"
- Log NO contiene el prompt enviado a OpenRouter
- Log NO contiene la respuesta completa de OpenRouter
- Log NO contiene el reasoning del modelo

### Fix Checking

**Goal**: Verificar que para todas las entradas donde las condiciones de bug se cumplen, las funciones corregidas producen el comportamiento esperado.

#### Bug 1: Airflow Substring Matching Fix

**Pseudocode:**
```
FOR ALL question WHERE 'airflow' IN question.lower() DO
  result := _handle_experience_question_fixed(question, question.lower(), 'number')
  ASSERT result.answer == '0'
  ASSERT 'NO tengo experiencia con Airflow' IN result.reasoning OR 'airflow' IN result.reasoning.lower()
  ASSERT result.confidence >= 0.9
END FOR
```

**Test Cases**:
- Pregunta "¿Cuántos años de experiencia tienes en Airflow?" → answer="0"
- Pregunta "How many years of experience do you have with Apache Airflow?" → answer="0"
- Pregunta "Do you have Airflow experience?" → answer="0"
- Verificar que el loop itera sobre 'airflow' antes de 'ai' después del ordenamiento

#### Bug 2: CV Radio Button Detection Fix

**Pseudocode:**
```
FOR ALL modal_state WHERE modal_state.has_cv_radio_buttons == True DO
  fields := detect_fields_fixed(modal_state.modal_element)
  cv_radio_fields := [f for f in fields if f.field_type == 'cv_radio']
  ASSERT len(cv_radio_fields) > 0
  ASSERT len(cv_radio_fields) == modal_state.expected_cv_count
END FOR
```

**Test Cases**:
- Modal con 1 CV pre-cargado → detect_fields retorna 1 FormField con field_type='cv_radio'
- Modal con 2 CVs pre-cargados → detect_fields retorna 2 FormField con field_type='cv_radio'
- Modal con 3 CVs pre-cargados → detect_fields retorna 3 FormField con field_type='cv_radio'
- Verificar que cada FormField tiene label correcto con nombre del archivo

#### Bug 3: CV Selection Fix

**Pseudocode:**
```
FOR ALL job WHERE modal_has_preloaded_cvs(job.modal) == True DO
  cv_recommendation := select_cv_by_keywords(job.title, job.description)
  result := handle_cv_upload_fixed(job, result_dict, search_context)
  
  ASSERT select_cv_by_keywords was called with (job.title, job.description)
  ASSERT cv_recommendation was used to select radio button
  ASSERT no new file was uploaded if matching CV exists
  ASSERT result == True
END FOR
```

**Test Cases**:
- Job title="Data Engineer" con CVs pre-cargados → selecciona "CV Automatización Data.pdf"
- Job title="Software Engineer" con CVs pre-cargados → selecciona "CV Software Engineer.pdf"
- Job con CVs pre-cargados pero ninguno coincide → sube nuevo archivo con recomendación AI
- Job sin CVs pre-cargados → sube archivo directamente (comportamiento preservado)

#### Bug 4: Job Description Expansion Fix

**Pseudocode:**
```
FOR ALL job WHERE job.has_expandable_description == True DO
  full_description := get_job_description_fixed(job)
  
  ASSERT expand_button was clicked
  ASSERT WebDriverWait was used to wait for content
  ASSERT full_description is not empty
  ASSERT len(full_description) > 100
  ASSERT no "no such element" error was raised
END FOR
```

**Test Cases**:
- Job con botón "Ver más" → descripción se expande → contenido se extrae exitosamente
- Job con botón "Show more" → descripción se expande → contenido se extrae exitosamente
- Job con contenido que tarda en renderizarse → espera explícita funciona → contenido se extrae
- Verificar que no hay falsos negativos (reportar error cuando la expansión fue exitosa)

#### Bug 5: Logging Fix

**Pseudocode:**
```
FOR ALL question WHERE question requires AI call DO
  with captured_logs:
    result := answer_question_fixed(question, field_type, cv_context)
  
  ASSERT 'SYSTEM PROMPT:' IN captured_logs
  ASSERT 'USER MESSAGE:' IN captured_logs
  ASSERT 'RAW RESPONSE:' IN captured_logs
  ASSERT 'JSON PARSEADO:' IN captured_logs
  ASSERT result.reasoning IN captured_logs
END FOR
```

**Test Cases**:
- Pregunta de experiencia → log contiene prompt completo, respuesta completa, JSON parseado
- Pregunta general → log contiene todos los pasos de la interacción con AI
- Pregunta con error de API → log contiene el error completo y el contexto
- Verificar que el reasoning del modelo está visible en el log

### Preservation Checking

**Goal**: Verificar que para todas las entradas donde las condiciones de bug NO se cumplen, las funciones corregidas producen exactamente el mismo resultado que las funciones originales.

#### Preservation 1: Existing Technology Experience

**Pseudocode:**
```
FOR ALL question WHERE question mentions tech WITH real_experience DO
  result_original := _handle_experience_question_original(question, question.lower(), field_type)
  result_fixed := _handle_experience_question_fixed(question, question.lower(), field_type)
  
  ASSERT result_original.answer == result_fixed.answer
  ASSERT result_original.confidence == result_fixed.confidence
  ASSERT result_original.reasoning == result_fixed.reasoning
END FOR
```

**Testing Approach**: Property-based testing es recomendado para preservation checking porque:
- Genera muchos casos de prueba automáticamente a través del dominio de entrada
- Detecta edge cases que los unit tests manuales podrían perder
- Proporciona garantías fuertes de que el comportamiento no cambia para todas las entradas no buggy

**Test Plan**: Observar comportamiento en código UNFIXED primero para tecnologías con experiencia real, luego escribir property-based tests capturando ese comportamiento.

**Test Cases**:
1. **Python Experience**: Pregunta "¿Cuántos años de experiencia tienes en Python?" → answer="5" (sin cambios)
2. **Ruby Experience**: Pregunta "How many years of Ruby experience?" → answer="3" (sin cambios)
3. **SQL Experience**: Pregunta "SQL experience years?" → answer="4" (sin cambios)
4. **AWS Experience**: Pregunta "AWS experience?" → answer="2" (sin cambios)
5. **Machine Learning**: Pregunta "Machine learning experience?" → answer="2" (sin cambios, coincidencia larga prioritaria)

#### Preservation 2: Other Field Detection

**Pseudocode:**
```
FOR ALL modal WHERE modal does NOT contain cv_radio fields DO
  fields_original := detect_fields_original(modal)
  fields_fixed := detect_fields_fixed(modal)
  
  ASSERT len(fields_original) == len(fields_fixed)
  FOR i in range(len(fields_original)):
    ASSERT fields_original[i].field_type == fields_fixed[i].field_type
    ASSERT fields_original[i].label == fields_fixed[i].label
    ASSERT fields_original[i].purpose == fields_fixed[i].purpose
  END FOR
END FOR
```

**Test Cases**:
1. **Text Fields**: Modal con campos de texto → detección sin cambios
2. **Email Fields**: Modal con campo de email → detección sin cambios
3. **Phone Fields**: Modal con campos de teléfono → detección sin cambios
4. **Dropdown Fields**: Modal con dropdowns → detección sin cambios
5. **Textarea Fields**: Modal con textareas → detección sin cambios
6. **File Input**: Modal con `input[type='file']` pero sin radio buttons → detección sin cambios

#### Preservation 3: CV Upload Without Pre-loaded CVs

**Pseudocode:**
```
FOR ALL job WHERE modal does NOT have preloaded CVs DO
  result_original := handle_cv_upload_original(job, result_dict, search_context)
  result_fixed := handle_cv_upload_fixed(job, result_dict, search_context)
  
  ASSERT result_original == result_fixed
  ASSERT same CV file was uploaded
  ASSERT same logging occurred
END FOR
```

**Test Cases**:
1. **First Time Application**: Usuario nunca subió CV → sistema sube archivo nuevo (sin cambios)
2. **Only File Input Available**: Modal solo tiene `input[type='file']` → sistema sube archivo (sin cambios)
3. **CV Selection Logic**: Sistema usa `select_cv_by_keywords()` para elegir archivo correcto (sin cambios)

#### Preservation 4: Non-expandable Descriptions

**Pseudocode:**
```
FOR ALL job WHERE job does NOT have expandable description DO
  description_original := get_job_description_original(job)
  description_fixed := get_job_description_fixed(job)
  
  ASSERT description_original == description_fixed
  ASSERT no errors occurred
END FOR
```

**Test Cases**:
1. **Short Description**: Job con descripción corta sin botón → extracción sin cambios
2. **Already Expanded**: Job con descripción ya expandida → extracción sin cambios
3. **No Expand Button**: Job sin botón de expansión → extracción sin cambios, sin errores

### Unit Tests

- Test `_handle_experience_question` con diferentes tecnologías (Airflow, Python, Ruby, etc.)
- Test `detect_fields` con diferentes estructuras de modal (con/sin radio buttons)
- Test `handle_cv_upload` con diferentes estados de modal (CVs pre-cargados, solo file input, etc.)
- Test job description expansion con diferentes estados (con/sin botón, timing, selectores)
- Test logging capturando output y verificando contenido

### Property-Based Tests

- Generar preguntas aleatorias sobre tecnologías y verificar que las respuestas son correctas
- Generar estructuras de modal aleatorias y verificar que la detección de campos funciona
- Generar job descriptions aleatorias y verificar que la selección de CV usa AI correctamente
- Generar estados de expansión aleatorios y verificar que no hay falsos negativos
- Verificar que todas las interacciones con AI están completamente loggeadas

### Integration Tests

- Test flujo completo de aplicación con pregunta sobre Airflow → verificar respuesta "0"
- Test flujo completo con CVs pre-cargados → verificar selección correcta basada en AI
- Test flujo completo con expansión de descripción → verificar extracción exitosa
- Test flujo completo verificando logs → verificar que todos los prompts y respuestas están registrados
- Test switching entre diferentes tipos de formularios y verificar comportamiento correcto
