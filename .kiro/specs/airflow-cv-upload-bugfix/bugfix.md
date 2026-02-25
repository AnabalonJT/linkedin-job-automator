# Bugfix Requirements Document

## Introduction

Este documento describe bugs críticos en el sistema de auto-aplicación de LinkedIn que causan respuestas incorrectas sobre experiencia tecnológica, fallos en la detección y selección de CVs, y problemas con la expansión de descripciones de trabajo. Los bugs incluyen: (1) respuestas falsas sobre experiencia con Airflow debido a substring matching, (2) fallo en detección de radio buttons de CV, (3) selección incorrecta de CV (siempre sube el mismo en lugar de usar el recomendado por AI o el ya seleccionado), y (4) falso positivo al expandir descripciones (reporta éxito pero luego falla al buscar el contenido expandido).

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN la pregunta contiene "Airflow" (ej: "¿Cuántos años de experiencia tienes en Airflow?") THEN el sistema responde "2" con reasoning "Años de experiencia con ai según CV"

1.2 WHEN el sistema busca coincidencias de tecnologías en `_handle_experience_question` THEN el substring "ai" en "Airflow" coincide con la entrada `'ai': '2'` en el diccionario `tech_experience` antes de verificar `'airflow': '0'`

1.3 WHEN el sistema procesa el paso 2 del formulario de aplicación que contiene sección de CV upload con radio buttons THEN detecta 0 campos en el formulario

1.4 WHEN el sistema busca campos con selector `'cv_radio': 'input[id*="jobsDocumentCardToggle"]'` dentro del modal THEN no encuentra los elementos de radio buttons de CV que existen en el DOM

1.5 WHEN el sistema llama `handle_cv_upload()` después de abrir el modal THEN siempre intenta subir un nuevo CV usando `input[type='file']` en lugar de verificar si ya hay CVs disponibles para seleccionar

1.6 WHEN LinkedIn ya tiene CVs cargados y muestra radio buttons para seleccionarlos THEN el sistema ignora estos CVs existentes y sube un archivo nuevo

1.7 WHEN el sistema selecciona qué CV usar THEN no utiliza la recomendación de AI basada en el job description, sino que siempre usa el mismo CV predeterminado

1.8 WHEN el sistema expande la descripción del trabajo con el botón `button[data-testid='expandable-text-button']` THEN el contenido se expande correctamente pero el sistema reporta error "no such element" al buscar `.jobs-description__content, .jobs-description`, causando un falso negativo

1.9 WHEN el sistema procesa preguntas de experiencia usando el handler especial THEN no registra en el log el prompt completo ni la respuesta completa del modelo AI, dificultando el debugging

### Expected Behavior (Correct)

2.1 WHEN la pregunta contiene "Airflow" (ej: "¿Cuántos años de experiencia tienes en Airflow?") THEN el sistema SHALL responder "0" con reasoning "NO tengo experiencia con Airflow según CV"

2.2 WHEN el sistema busca coincidencias de tecnologías en `_handle_experience_question` THEN el sistema SHALL verificar coincidencias exactas o más específicas primero, evitando que substrings cortos como "ai" coincidan incorrectamente con tecnologías como "Airflow"

2.3 WHEN el sistema procesa el paso 2 del formulario de aplicación que contiene sección de CV upload con radio buttons THEN el sistema SHALL detectar los campos de CV radio buttons correctamente

2.4 WHEN el sistema busca campos con selector `'cv_radio': 'input[id*="jobsDocumentCardToggle"]'` dentro del modal THEN el sistema SHALL encontrar y retornar los elementos de radio buttons de CV disponibles

2.5 WHEN el sistema llama `handle_cv_upload()` después de abrir el modal THEN el sistema SHALL primero verificar si existen CVs ya cargados (radio buttons) antes de intentar subir un nuevo archivo

2.6 WHEN LinkedIn ya tiene CVs cargados y muestra radio buttons para seleccionarlos THEN el sistema SHALL detectar estos CVs, usar AI para recomendar el más apropiado según job description, y seleccionar el radio button correspondiente

2.7 WHEN el sistema selecciona qué CV usar THEN el sistema SHALL utilizar la función `select_cv_by_keywords()` con el job title y description para obtener la recomendación de AI del CV más apropiado

2.8 WHEN el sistema expande la descripción del trabajo con el botón `button[data-testid='expandable-text-button']` THEN el sistema SHALL buscar el contenido expandido usando selectores correctos que funcionen después de la expansión, evitando falsos negativos

2.9 WHEN el sistema procesa preguntas de experiencia usando el handler especial o llamando a OpenRouter API THEN el sistema SHALL registrar en el log el prompt completo enviado y la respuesta completa recibida para facilitar debugging

### Unchanged Behavior (Regression Prevention)

3.1 WHEN la pregunta contiene tecnologías con experiencia real como "Python", "SQL", "AWS", "Ruby" THEN el sistema SHALL CONTINUE TO responder con los años correctos según cv_context.json

3.2 WHEN el sistema busca coincidencias de tecnologías con nombres largos como "machine learning", "apache airflow", "apache spark" THEN el sistema SHALL CONTINUE TO priorizar coincidencias más largas primero (ordenamiento por longitud descendente)

3.3 WHEN el sistema detecta otros tipos de campos (text, numeric, email, phone, dropdown, textarea) en el formulario THEN el sistema SHALL CONTINUE TO detectarlos correctamente

3.4 WHEN el sistema procesa pasos del formulario que no contienen campos de CV THEN el sistema SHALL CONTINUE TO detectar y llenar los campos normalmente

3.5 WHEN la pregunta contiene tecnologías con 0 años de experiencia como "kubernetes", "spark", "kafka" THEN el sistema SHALL CONTINUE TO responder "0" correctamente

3.6 WHEN no hay CVs pre-cargados en LinkedIn y solo existe `input[type='file']` THEN el sistema SHALL CONTINUE TO subir el CV apropiado usando `send_keys()` con la ruta del archivo

3.7 WHEN el sistema llena campos de texto, email, teléfono, y dropdowns THEN el sistema SHALL CONTINUE TO usar los valores correctos de cv_context.json y respuestas_comunes.json

3.8 WHEN el sistema encuentra descripciones de trabajo que no tienen botón de expandir THEN el sistema SHALL CONTINUE TO procesar la descripción visible sin errores
