#!/usr/bin/env python3
"""
LinkedIn Job Applier
Aplica automáticamente a trabajos con Easy Apply usando IA
"""

import time
import json
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys

from utils import Config, Logger
from models import ApplicationResult, ProcessedJob, ApplicationDecision
from modal_detector import ModalDetector
from form_field_detector import FormFieldDetector
from cv_selector import CVSelector
from question_handler import QuestionHandler
from confidence_system import ConfidenceSystem
from state_manager import StateManager
from google_sheets_updater import GoogleSheetsUpdater
from telegram_notifier import TelegramNotifierWithAccumulation

# Optional: Telegram notifier (graceful if env not configured)
try:
    from telegram_notifier import TelegramNotifier
except Exception:
    TelegramNotifier = None


class LinkedInApplier:
    """Aplicador automático a trabajos de LinkedIn con IA"""
    
    def __init__(self, driver, config: Config, logger: Logger):
        self.driver = driver
        self.config = config
        self.logger = logger
        
        # Cargar respuestas configuradas (legacy, para fallback)
        self.answers = config.load_json_config('respuestas_comunes.json')
        
        # Cargar rutas de CVs
        self.cv_paths = config.get_cv_paths()
        
        # Initialize new components with correct signatures
        self.modal_detector = ModalDetector(poll_interval=0.5)
        self.form_detector = FormFieldDetector()
        self.cv_selector = CVSelector(api_key=config.get_env_var('OPENROUTER_API_KEY'))
        self.question_handler = QuestionHandler(
            api_key=config.get_env_var('OPENROUTER_API_KEY'),
            common_answers_path="config/respuestas_comunes.json"
        )
        self.confidence_system = ConfidenceSystem(
            high_threshold=float(config.get_env_var('HIGH_THRESHOLD', '0.85')),
            low_threshold=float(config.get_env_var('LOW_THRESHOLD', '0.65'))
        )
        self.state_manager = StateManager(state_file="data/logs/application_state.json")
        
        # Initialize Google Sheets updater (optional)
        self.sheets_updater = None
        try:
            sheets_id = config.get_env_var('GOOGLE_SHEETS_ID')
            credentials_path = 'config/google_credentials.json'
            if sheets_id and Path(credentials_path).exists():
                self.sheets_updater = GoogleSheetsUpdater(credentials_path, sheets_id)
                logger.info('✓ Google Sheets updater initialized')
        except Exception as e:
            logger.warning(f'Google Sheets not available: {e}')
        
        # Initialize Telegram notifier with accumulation
        self.telegram_notifier = None
        try:
            self.telegram_notifier = TelegramNotifierWithAccumulation()
            logger.info('✓ Telegram notifier initialized')
        except Exception as e:
            logger.warning(f'Telegram not configured: {e}')
    
    def _update_sheets(self, job: Dict[str, Any], result: Dict[str, Any]):
        """
        Helper method to update Google Sheets with proper parameter extraction.
        
        Args:
            job: Job dictionary with title, company, url, location
            result: Result dictionary with status, cv_used, error, questions_answered, confidence_score
        """
        if not self.sheets_updater:
            return
        
        try:
            # Extract questions answered count
            questions_answered = len(result.get('questions_answered', []))
            
            # Calculate average confidence
            average_confidence = 0.0
            if result.get('confidence_score'):
                average_confidence = result['confidence_score']
            elif result.get('questions_answered'):
                confidences = [qa.get('confidence', 0.0) for qa in result['questions_answered']]
                if confidences:
                    average_confidence = sum(confidences) / len(confidences)
            
            # Build notes
            notes = result.get('error', '')
            if result.get('low_confidence_questions'):
                low_conf_questions = result['low_confidence_questions']
                questions_text = ', '.join(low_conf_questions[:3])
                if len(low_conf_questions) > 3:
                    questions_text += f' (y {len(low_conf_questions) - 3} más)'
                notes = f"{notes}. Preguntas con baja confianza: {questions_text}" if notes else f"Preguntas con baja confianza: {questions_text}"
            
            # Call with correct parameters
            self.sheets_updater.update_application(
                job_id=job.get('id', ''),
                job_url=job['url'],
                job_title=job['title'],
                company=job['company'],
                location=job.get('location', 'N/A'),
                status=result['status'],
                cv_used=result.get('cv_used'),
                notes=notes,
                questions_answered=questions_answered,
                average_confidence=average_confidence
            )
        except Exception as e:
            self.logger.warning(f"Error updating Google Sheets: {e}")
    
    def _is_job_unavailable(self) -> bool:
        """
        Verifica si el trabajo ya no acepta postulaciones
        
        Returns:
            True si el trabajo está cerrado/no disponible
        """
        try:
            closed_indicators = [
                "No longer accepting applications",
                "Ya no se aceptan solicitudes",
                "This job is no longer available",
                "Este trabajo ya no está disponible",
                "Closed",
                "Cerrado"
            ]
            
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            return any(indicator.lower() in page_text.lower() for indicator in closed_indicators)
        except Exception:
            return False
    
    def _expand_job_description(self, job: Dict[str, Any]) -> str:
        """
        Expande la descripción completa del trabajo si hay botón "Ver más"
        
        Args:
            job: Datos del trabajo
        
        Returns:
            Descripción completa del trabajo
        """
        try:
            self.logger.info("  Intentando expandir descripción...")
            
            # Buscar botones de expansión (múltiples intentos)
            expand_selectors = [
                "button[aria-label*='Ver más']",
                "button[aria-label*='Show more']",
                "button[aria-label*='See more']",
                "button.jobs-description__footer-button",
                "button[data-testid='expandable-text-button']",  # Nuevo selector
                "button:has-text('más')",  # Botón con texto "más"
            ]
            
            button_clicked = False
            for selector in expand_selectors:
                try:
                    expand_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if expand_button.is_displayed():
                        self.logger.info(f"  Botón encontrado: {selector}")
                        # Scroll al botón primero
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", expand_button)
                        time.sleep(0.5)
                        # Click usando JavaScript para mayor confiabilidad
                        self.driver.execute_script("arguments[0].click();", expand_button)
                        self.logger.info(f"  Clic ejecutado, esperando renderizado...")
                        button_clicked = True
                        
                        # Bug 4 fix: Add explicit wait for content to render
                        from selenium.webdriver.support.ui import WebDriverWait
                        from selenium.webdriver.support import expected_conditions as EC
                        from selenium.common.exceptions import TimeoutException
                        
                        try:
                            # Esperar a que el contenido expandido esté presente
                            WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "div.jobs-description__content, div[class*='jobs-description']"))
                            )
                            self.logger.info("  ✓ Contenido expandido renderizado")
                        except TimeoutException:
                            self.logger.warning("  Timeout esperando contenido expandido, continuando...")
                        
                        time.sleep(1)  # Espera adicional para asegurar renderizado completo
                        break
                except NoSuchElementException:
                    continue
                except Exception as e:
                    self.logger.info(f"  Error con selector {selector}: {e}")
                    continue
            
            # Bug 4 fix: Selectores mejorados que funcionan post-expansión
            self.logger.info(f"  Buscando contenido con {5} selectores...")
            description_selectors = [
                "div.jobs-description__content",  # Más específico
                "div[class*='jobs-description__content']",
                ".jobs-description",
                "article.jobs-description",
                "section.jobs-description",
                ".jobs-box__html-content"
            ]
            
            for desc_selector in description_selectors:
                try:
                    description_element = self.driver.find_element(By.CSS_SELECTOR, desc_selector)
                    full_description = description_element.text
                    if full_description and len(full_description) > 50:  # Verificar que tenga contenido real
                        self.logger.info(f"  ✓ Descripción extraída: {len(full_description)} caracteres")
                        return full_description
                except NoSuchElementException:
                    continue
            
            # Bug 4 fix: Mejorar manejo de errores para evitar falsos negativos
            # Si se hizo clic en el botón pero no se encontró contenido, verificar si el botón desapareció
            if button_clicked:
                try:
                    # Verificar si el botón de expansión ya no está visible (señal de que se expandió)
                    expand_button = self.driver.find_element(By.CSS_SELECTOR, expand_selectors[0])
                    if not expand_button.is_displayed():
                        self.logger.info("  ✓ Botón de expansión no visible (contenido expandido)")
                except NoSuchElementException:
                    self.logger.info("  ✓ Botón de expansión no encontrado (ya expandido)")
            
            # Si no se pudo extraer con selectores, intentar obtener todo el texto visible
            self.logger.warning(f"  No se pudo extraer descripción con selectores específicos, usando fallback...")
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            # Buscar la sección que parece ser la descripción (heurística)
            if len(body_text) > 100:
                self.logger.info(f"  ✓ Descripción extraída (fallback, {len(body_text)} caracteres)")
                return body_text
            
            return job.get('description', '')
            
        except Exception as e:
            self.logger.warning(f"  Error expandiendo descripción: {e}")
            return job.get('description', '')
    
    def _click_easy_apply_button(self, result: Dict[str, Any]) -> bool:
        """
        Busca y hace clic en el botón Easy Apply
        
        Args:
            result: Diccionario de resultado (se modifica)
        
        Returns:
            True si se hizo clic exitosamente
        """
        try:
            easy_apply_button = None
            selectors = [
                # Botones tradicionales
                "button.jobs-apply-button",
                "button[aria-label*='Solicitud sencilla']",
                "button[aria-label*='Easy Apply']",
                "button#jobs-apply-button-id",
                "button[data-live-test-job-apply-button]",
                # Links que funcionan como botones
                "a[aria-label*='Solicitud sencilla']",
                "a[aria-label*='Easy Apply']",
                "a.jobs-apply-button"
            ]
            
            for selector in selectors:
                try:
                    easy_apply_button = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if easy_apply_button:
                        self.logger.info(f"  ✓ Botón Easy Apply encontrado con: {selector}")
                        break
                except TimeoutException:
                    continue
            
            if not easy_apply_button:
                # Verificar si requiere postulación externa
                try:
                    external_apply = self.driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='Postular'], a[aria-label*='Apply']")
                    if external_apply:
                        result['error'] = "Requiere postulación externa (no Easy Apply)"
                        result['status'] = 'MANUAL'
                        self.logger.warning("✗ Trabajo requiere postulación externa")
                        return False
                except Exception:
                    pass
                
                result['error'] = "No se encontró botón Easy Apply"
                result['status'] = 'MANUAL'
                self.logger.warning("✗ No se encontró botón Easy Apply")
                
                # Guardar screenshot para debug
                self._save_debug_screenshot("no_easy_apply_button")
                
                return False
            
            # Click en el botón/link
            # Guardar URL antes del clic
            url_before = self.driver.current_url
            is_link = easy_apply_button.tag_name == 'a'
            
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", easy_apply_button)
                time.sleep(1)
                
                # Si es un link, intentar navegar directamente a la URL
                if is_link:
                    href = easy_apply_button.get_attribute('href')
                    if href:
                        self.logger.info(f"  → Es un link, navegando a: {href[:80]}...")
                        self.driver.get(href)
                        time.sleep(3)
                        self.logger.info(f"  ✓ Navegación completada")
                    else:
                        # Si no tiene href, hacer clic normal
                        easy_apply_button.click()
                        time.sleep(3)
                else:
                    # Es un botón, hacer clic normal
                    easy_apply_button.click()
                    self.logger.info("  ✓ Click en Easy Apply realizado")
                    time.sleep(3)
                    
            except Exception as e:
                # Fallback a JavaScript
                self.logger.warning(f"  Click/navegación falló, usando JavaScript...")
                if is_link:
                    href = easy_apply_button.get_attribute('href')
                    if href:
                        self.driver.execute_script(f"window.location.href = '{href}';")
                    else:
                        self.driver.execute_script("arguments[0].click();", easy_apply_button)
                else:
                    self.driver.execute_script("arguments[0].click();", easy_apply_button)
                time.sleep(3)
            
            # Verificar si la URL cambió
            url_after = self.driver.current_url
            if url_after != url_before:
                self.logger.info(f"  ✓ URL cambió después del clic")
                self.logger.info(f"    Antes: {url_before[:80]}...")
                self.logger.info(f"    Después: {url_after[:80]}...")
            else:
                self.logger.info(f"  → URL no cambió (modal overlay esperado)")
            
            return True
            
        except Exception as e:
            result['error'] = f"Error haciendo clic en Easy Apply: {str(e)}"
            result['status'] = 'ERROR'
            self.logger.error(f"  ✗ {result['error']}")
            return False
    
    def _save_debug_screenshot(self, suffix: str):
        """Guarda screenshot para debugging"""
        try:
            screenshot_path = Path(f"data/logs/debug_{suffix}_{int(time.time())}.png")
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            self.driver.save_screenshot(str(screenshot_path))
            self.logger.info(f"  Screenshot guardado: {screenshot_path}")
        except Exception as e:
            self.logger.warning(f"  No se pudo guardar screenshot: {e}")
    
    def _save_debug_html(self, job: Dict[str, Any], suffix: str):
        """Guarda HTML para debugging"""
        try:
            html_content = self.driver.execute_script("return document.body.innerHTML;")
            html_path = Path(f"data/logs/debug_{suffix}_{job['title'][:30]}_{int(time.time())}.html")
            html_path.parent.mkdir(parents=True, exist_ok=True)
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            self.logger.info(f"  HTML guardado: {html_path}")
        except Exception as e:
            self.logger.warning(f"  No se pudo guardar HTML: {e}")
    
    def _process_application_form_with_ai(
        self, 
        job: Dict[str, Any], 
        result: Dict[str, Any], 
        modal_element,
        cv_recommendation,
        full_description: str
    ) -> bool:
        """
        Procesa el formulario de aplicación multi-paso usando IA
        
        Args:
            job: Datos del trabajo
            result: Diccionario de resultado (se modifica)
            modal_element: Elemento del modal
            cv_recommendation: Recomendación de CV de la IA
            full_description: Descripción completa del trabajo
        
        Returns:
            True si se completó exitosamente
        """
        max_steps = 10
        current_step = 0
        questions_answered = []
        
        # Infinite loop detection: track field signatures
        previous_field_signatures = []
        loop_detection_threshold = 3  # If same fields appear 3 times, it's a loop
        
        # CV context para la IA (cargar desde archivo o config)
        cv_context = self._load_cv_context(cv_recommendation)
        
        while current_step < max_steps:
            current_step += 1
            self.logger.info(f"  Paso {current_step}...")
            time.sleep(2)
            
            # 1. Detectar campos del formulario
            fields = self.form_detector.detect_fields(modal_element)
            self.logger.info(f"  → Detectados {len(fields)} campos en el formulario")
            
            # Create signature of current fields for loop detection
            current_signature = tuple(sorted([f"{f.field_type}:{f.purpose}" for f in fields]))
            
            # Check for infinite loop
            if current_signature in previous_field_signatures:
                loop_count = previous_field_signatures.count(current_signature) + 1
                self.logger.warning(f"  ⚠ Mismos campos detectados {loop_count} veces")
                
                if loop_count >= loop_detection_threshold:
                    self.logger.error(f"  ✗ LOOP INFINITO DETECTADO - Mismos {len(fields)} campos aparecen {loop_count} veces sin cambios")
                    self.logger.error(f"     Los campos NO se están llenando correctamente")
                    result['status'] = 'MANUAL'
                    result['error'] = f"Loop infinito: {len(fields)} campos no se llenan (aparecieron {loop_count} veces)"
                    result['questions_answered'] = questions_answered
                    
                    # Save debug info
                    self._save_debug_screenshot(f"infinite_loop_step{current_step}")
                    self._save_debug_html(job, f"infinite_loop_step{current_step}")
                    
                    # Close modal
                    self._close_modal()
                    return False
            
            previous_field_signatures.append(current_signature)
            
            # Log cada campo detectado
            for field in fields:
                self.logger.info(f"    Campo: tipo={field.field_type}, propósito={field.purpose}")
            
            # 2. Llenar campos con IA
            fields_filled = 0
            for field in fields:
                # Skip si ya tiene valor (excepto radio buttons que siempre necesitan verificación)
                if field.field_type not in ['cv_radio', 'radio', 'checkbox']:
                    current_value = field.element.get_attribute('value')
                    if current_value:
                        self.logger.info(f"      → Campo ya tiene valor: {current_value[:30]}...")
                        continue
                
                # Manejar upload de CV (tanto file input como radio buttons)
                if field.field_type in ['file', 'cv_radio']:
                    success = self._handle_cv_upload_with_ai(field, cv_recommendation, result)
                    if success:
                        fields_filled += 1
                    continue
                
                # Para otros campos, usar IA para responder
                question_text = field.purpose or field.label or field.placeholder
                
                if not question_text:
                    self.logger.warning(f"    Campo sin propósito identificable, saltando...")
                    continue
                
                # Obtener respuesta de la IA
                answer_data = self.question_handler.answer_question(
                    question=question_text,
                    field_type=field.field_type,
                    cv_context=cv_context,
                    available_options=field.options
                )
                
                if answer_data:
                    # Log pregunta y respuesta
                    self.logger.info(f"    Pregunta: {question_text}")
                    self.logger.info(f"    Respuesta: {answer_data.answer} | Confianza: {answer_data.confidence:.2f}")
                    self.logger.info(f"    Razón: {answer_data.reasoning}")
                    
                    # Llenar campo
                    success = self._fill_field_with_answer(field, answer_data)
                    
                    if success:
                        fields_filled += 1
                        questions_answered.append({
                            'question': question_text,
                            'answer': answer_data.answer,
                            'confidence': answer_data.confidence,
                            'reasoning': answer_data.reasoning
                        })
                    else:
                        self.logger.warning(f"    ✗ No se pudo llenar campo")
                        # Guardar screenshot para debug
                        self._save_debug_screenshot(f"field_fill_failure_step{current_step}")
                else:
                    self.logger.warning(f"    ? No se pudo obtener respuesta de IA para: {question_text}")
            
            self.logger.info(f"  → {fields_filled} de {len(fields)} campos llenados en este paso")
            
            # 2.5. Si no se detectaron campos, buscar input de archivo para CV upload
            # Esto maneja el caso donde step 2 tiene file input pero no radio buttons
            if len(fields) == 0:
                self.logger.info("  → No se detectaron campos, buscando input de archivo para CV...")
                try:
                    # Buscar input de archivo dentro del modal
                    file_inputs = modal_element.find_elements(By.CSS_SELECTOR, "input[type='file']")
                    
                    if file_inputs:
                        self.logger.info(f"  → Encontrado {len(file_inputs)} input(s) de archivo")
                        
                        # Mapeo de tipos de CV a archivos reales
                        cv_files = {
                            'engineer_en': 'CV_ML_Data_Engineer_Jose_Tomas_Anabalon_EN.docx.pdf',
                            'engineer_es': 'CV Automatización_Data Anabalón.pdf',
                            'software_en': 'CV_Software_Engineer_Jose_Tomas_Anabalon_EN.docx.pdf',
                            'software_es': 'CV Software Engineer Anabalon.pdf'
                        }
                        
                        # Construir la clave del CV
                        cv_key = f"{cv_recommendation.cv_type}_{cv_recommendation.language}"
                        cv_filename = cv_files.get(cv_key)
                        
                        if not cv_filename:
                            self.logger.warning(f"  No se encontró mapeo para CV: {cv_key}")
                            cv_filename = f"CV {cv_recommendation.cv_type.title()} {'Anabalon' if cv_recommendation.language == 'en' else 'Anabalón'}.pdf"
                        
                        cv_path = Path(f"config/{cv_filename}")
                        
                        if cv_path.exists():
                            # Subir CV al primer input de archivo
                            file_inputs[0].send_keys(str(cv_path.absolute()))
                            self.logger.info(f"  ✓ CV subido: {cv_filename}")
                            result['cv_used'] = cv_key
                            time.sleep(2)
                        else:
                            self.logger.warning(f"  CV no encontrado: {cv_path}")
                            self.logger.warning(f"  Archivos disponibles en config/:")
                            for f in Path("config").glob("*.pdf"):
                                self.logger.warning(f"    - {f.name}")
                    else:
                        self.logger.info("  → No se encontró input de archivo")
                        
                except Exception as e:
                    self.logger.warning(f"  Error buscando/subiendo CV: {e}")
            
            # 3. Buscar y hacer clic en botón siguiente/enviar
            time.sleep(1)
            
            button_result = self._click_next_or_submit_button()
            
            if not button_result['found']:
                self.logger.warning("  ⚠ No se encontró botón de acción")
                result['error'] = f"No se encontró botón en paso {current_step}"
                result['status'] = 'MANUAL'
                result['questions_answered'] = questions_answered
                return False
            
            self.logger.info(f"  ✓ Click en botón: '{button_result.get('button_text', 'Unknown')}'")
            time.sleep(2)
            
            # 4. Si era botón de envío, evaluar confianza y decidir
            if button_result.get('is_submit'):
                self.logger.info("  → Botón de envío detectado, evaluando confianza...")
                
                # Convertir a QuestionAnswer objects para el sistema de confianza
                from models import QuestionAnswer
                qa_objects = [
                    QuestionAnswer(
                        question=qa['question'],
                        answer=qa['answer'],
                        confidence=qa['confidence'],
                        reasoning=qa['reasoning'],
                        sources=[]
                    )
                    for qa in questions_answered
                ]
                
                # Evaluar confianza
                decision = self.confidence_system.evaluate_application(qa_objects)
                
                result['confidence_score'] = decision.overall_confidence
                result['questions_answered'] = questions_answered
                
                self.logger.info(f"  → Decisión: {decision.action} (confianza: {decision.overall_confidence:.2f})")
                self.logger.info(f"    Razón: {decision.reasoning}")
                
                if decision.action == 'SUBMIT':
                    # Enviar aplicación
                    self.logger.success("  ✓ Confianza alta - Enviando aplicación")
                    result['status'] = 'APPLIED'
                    result['success'] = True
                    return True
                    
                elif decision.action == 'UNCERTAIN':
                    # Enviar pero marcar como inseguro
                    self.logger.warning("  ⚠ Confianza media - Enviando pero marcando como INSEGURO")
                    result['status'] = 'INSEGURO'
                    result['success'] = True
                    result['low_confidence_questions'] = decision.low_confidence_questions
                    return True
                    
                else:  # MANUAL
                    # No enviar, requiere revisión manual
                    self.logger.warning("  ✗ Confianza baja - Requiere revisión manual")
                    result['status'] = 'MANUAL'
                    result['error'] = f"Confianza insuficiente ({decision.overall_confidence:.2f})"
                    result['low_confidence_questions'] = decision.low_confidence_questions
                    
                    # Cerrar modal sin enviar
                    self._close_modal()
                    return False
        
        # Si llegamos aquí, se alcanzó el límite de pasos
        self.logger.warning(f"  Se alcanzó el límite de {max_steps} pasos")
        result['status'] = 'MANUAL'
        result['error'] = f"Se alcanzó límite de {max_steps} pasos sin completar"
        result['questions_answered'] = questions_answered
        return False
    
    def _load_cv_context(self, cv_recommendation) -> dict:
        """Carga el contexto del CV para la IA"""
        try:
            cv_context_path = Path("config/cv_context.json")
            if cv_context_path.exists():
                with open(cv_context_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Intentar parsear JSON, manejando errores de formato
                    try:
                        context = json.loads(content)
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"  Error parseando JSON (línea {e.lineno}): {e.msg}")
                        # Intentar cargar solo hasta el primer cierre de llave válido
                        try:
                            # Buscar el primer objeto JSON completo
                            brace_count = 0
                            for i, char in enumerate(content):
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        # Encontramos el cierre del primer objeto
                                        context = json.loads(content[:i+1])
                                        self.logger.info(f"  ✓ Contexto de CV cargado (parcial)")
                                        return context
                        except:
                            pass
                        # Si falla, usar fallback
                        return self.answers.get('informacion_personal', {})
                    
                self.logger.info(f"  ✓ Contexto de CV cargado desde {cv_context_path}")
                return context
            else:
                self.logger.warning(f"  Archivo de contexto no encontrado: {cv_context_path}")
                # Fallback a respuestas_comunes.json
                return self.answers.get('informacion_personal', {})
        except Exception as e:
            self.logger.warning(f"  Error cargando contexto de CV: {e}")
            return self.answers.get('informacion_personal', {})
    
    def _handle_cv_upload_with_ai(self, field, cv_recommendation, result):
        """Maneja la subida de CV usando la recomendación de IA"""
        try:
            # Verificar si es un radio button para seleccionar CV ya cargado
            if field.field_type == 'cv_radio':
                self.logger.info(f"  → Detectado radio button de CV ya cargado")
                
                # Obtener el label asociado para ver el nombre del archivo
                try:
                    field_id = field.element.get_attribute('id')
                    parent = field.element.find_element(By.XPATH, "../..")
                    
                    # Buscar el nombre del archivo en el card
                    file_name_element = parent.find_element(By.CSS_SELECTOR, ".jobs-document-upload-redesign-card__file-name")
                    file_name = file_name_element.text.strip()
                    
                    self.logger.info(f"  → CV disponible: {file_name}")
                    
                    # Bug 3 fix: Usar helper method para verificar coincidencia con recomendación
                    if self._matches_recommendation(file_name, cv_recommendation):
                        self.logger.info(f"  ✓ CV coincide con recomendación ({cv_recommendation.cv_type}), seleccionando...")
                        
                        # Hacer clic en el radio button
                        if not field.element.is_selected():
                            # Buscar el label asociado y hacer clic en él
                            label = parent.find_element(By.CSS_SELECTOR, f"label[for='{field_id}']")
                            label.click()
                            time.sleep(1)
                            self.logger.info(f"  ✓ CV seleccionado: {file_name}")
                            result['cv_used'] = f"{cv_recommendation.cv_type}_{cv_recommendation.language}"
                            return True
                        else:
                            self.logger.info(f"  ✓ CV ya estaba seleccionado: {file_name}")
                            result['cv_used'] = f"{cv_recommendation.cv_type}_{cv_recommendation.language}"
                            return True
                    else:
                        self.logger.info(f"  → CV no coincide con recomendación, buscando siguiente...")
                        return False
                        
                except Exception as e:
                    self.logger.warning(f"  Error procesando radio button de CV: {e}")
                    return False
            
            # Si es un input file tradicional, subir el archivo
            # Mapeo de tipos de CV a archivos reales
            cv_files = {
                'engineer_en': 'CV_ML_Data_Engineer_Jose_Tomas_Anabalon_EN.docx.pdf',
                'engineer_es': 'CV Automatización_Data Anabalón.pdf',
                'software_en': 'CV_Software_Engineer_Jose_Tomas_Anabalon_EN.docx.pdf',
                'software_es': 'CV Software Engineer Anabalon.pdf'
            }
            
            # Construir la clave del CV
            cv_key = f"{cv_recommendation.cv_type}_{cv_recommendation.language}"
            cv_filename = cv_files.get(cv_key)
            
            if not cv_filename:
                self.logger.warning(f"  No se encontró mapeo para CV: {cv_key}")
                # Fallback al nombre antiguo
                cv_filename = f"CV {cv_recommendation.cv_type.title()} {'Anabalon' if cv_recommendation.language == 'en' else 'Anabalón'}.pdf"
            
            cv_path = Path(f"config/{cv_filename}")
            
            if not cv_path.exists():
                self.logger.warning(f"  CV no encontrado: {cv_path}")
                self.logger.warning(f"  Archivos disponibles en config/:")
                for f in Path("config").glob("*.pdf"):
                    self.logger.warning(f"    - {f.name}")
                return False
            
            field.element.send_keys(str(cv_path.absolute()))
            self.logger.info(f"  ✓ CV subido: {cv_filename}")
            result['cv_used'] = cv_key
            time.sleep(2)
            return True
            
        except Exception as e:
            self.logger.warning(f"  Error subiendo CV: {e}")
            return False
    
    def _matches_recommendation(self, file_name: str, cv_recommendation) -> bool:
        """
        Bug 3 fix: Verifica si un CV coincide con la recomendación de AI.
        
        Args:
            file_name: Nombre del archivo CV
            cv_recommendation: CVRecommendation object con cv_type y language
            
        Returns:
            True si el CV coincide con la recomendación
        """
        try:
            file_name_lower = file_name.lower()
            
            # Definir keywords para cada tipo de CV
            cv_keywords = {
                'software': ['software', 'engineer', 'backend', 'fullstack', 'full stack', 'developer'],
                'engineer': ['automatización', 'automation', 'data', 'ml', 'ai', 'machine learning', 'ingeniero']
            }
            
            # Obtener keywords del tipo recomendado
            keywords = cv_keywords.get(cv_recommendation.cv_type, [])
            
            # Verificar si algún keyword está en el nombre del archivo
            match = any(keyword.lower() in file_name_lower for keyword in keywords)
            
            if match:
                self.logger.info(f"  CV '{file_name}' coincide con tipo '{cv_recommendation.cv_type}'")
            else:
                self.logger.info(f"  CV '{file_name}' NO coincide con tipo '{cv_recommendation.cv_type}'")
            
            return match
            
        except Exception as e:
            self.logger.info(f"Error verificando match de CV: {e}")
            return False
    
    def _fill_field_with_answer(self, field, answer_data) -> bool:
        """
        Llena un campo con la respuesta de la IA
        
        Args:
            field: FormField object
            answer_data: QuestionAnswer object
        
        Returns:
            True si se llenó exitosamente
        """
        try:
            element = field.element
            
            # Intentar con Selenium primero
            try:
                if field.field_type == 'dropdown':
                    from selenium.webdriver.support.ui import Select
                    select = Select(element)
                    
                    # Primero intentar coincidencia exacta (case-insensitive)
                    answer_lower = answer_data.answer.lower().strip()
                    for option in select.options:
                        option_text = option.text.strip()
                        if option_text.lower() == answer_lower:
                            select.select_by_visible_text(option_text)
                            self.logger.info(f"      ✓ Dropdown seleccionado (coincidencia exacta): {option_text}")
                            return True
                    
                    # Si no hay coincidencia exacta, buscar coincidencia parcial
                    for option in select.options:
                        option_text = option.text.strip()
                        # Buscar si la respuesta está contenida en la opción O viceversa
                        if answer_lower in option_text.lower() or option_text.lower() in answer_lower:
                            select.select_by_visible_text(option_text)
                            self.logger.info(f"      ✓ Dropdown seleccionado (coincidencia parcial): {option_text}")
                            return True
                    
                    # Si no se encontró coincidencia, loguear las opciones disponibles
                    self.logger.warning(f"      ✗ No se encontró coincidencia para '{answer_data.answer}'")
                    self.logger.warning(f"      Opciones disponibles:")
                    for option in select.options:
                        self.logger.warning(f"        - {option.text.strip()}")
                    return False
                    
                elif field.field_type in ['radio', 'checkbox']:
                    # Buscar el radio/checkbox correcto
                    parent = element.find_element(By.XPATH, "..")
                    labels = parent.find_elements(By.TAG_NAME, "label")
                    for label in labels:
                        if answer_data.answer.lower() in label.text.lower():
                            label.click()
                            return True
                    return False
                    
                else:  # text, email, phone, textarea, numeric
                    # Para campos numéricos y de texto, usar JavaScript para mayor confiabilidad
                    self.logger.info(f"      → Llenando campo {field.field_type} con: {answer_data.answer}")
                    
                    # Primero intentar con Selenium
                    element.clear()
                    element.send_keys(answer_data.answer)
                    
                    # Verificar que el valor se haya establecido
                    current_value = element.get_attribute('value')
                    if current_value == answer_data.answer:
                        self.logger.info(f"      ✓ Campo llenado correctamente (Selenium)")
                        return True
                    else:
                        # Si no funcionó, usar JavaScript
                        self.logger.warning(f"      Selenium no estableció el valor, usando JavaScript...")
                        self.driver.execute_script(
                            """
                            arguments[0].value = arguments[1];
                            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                            arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
                            """,
                            element,
                            answer_data.answer
                        )
                        
                        # Verificar nuevamente
                        current_value = element.get_attribute('value')
                        if current_value == answer_data.answer:
                            self.logger.info(f"      ✓ Campo llenado correctamente (JavaScript)")
                            return True
                        else:
                            self.logger.warning(f"      ✗ No se pudo establecer el valor. Esperado: {answer_data.answer}, Actual: {current_value}")
                            return False
                    
            except Exception as e:
                # Fallback a JavaScript
                self.logger.warning(f"    Selenium falló, usando JavaScript: {e}")
                self.driver.execute_script(
                    """
                    arguments[0].value = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
                    """,
                    element,
                    answer_data.answer
                )
                return True
                
        except Exception as e:
            self.logger.warning(f"    Error llenando campo: {e}")
            return False
    
    def _click_next_or_submit_button(self) -> dict:
        """
        Busca y hace clic en el botón siguiente o enviar
        
        Returns:
            Dict con {found: bool, is_submit: bool, button_text: str}
        """
        try:
            click_script = """
            let debug = {
                total_buttons: document.querySelectorAll('button').length,
                visible_buttons: 0,
                buttons_found: []
            };
            
            // Buscar botón de acción
            const buttonSelectors = [
                'button[data-easy-apply-next-button]',
                'button[aria-label*="siguiente"]',
                'button[aria-label*="Next"]',
                'button[aria-label*="Enviar"]',
                'button[aria-label*="Submit"]',
                'button[aria-label*="Revisar"]',
                'button[aria-label*="Review"]',
                'button.artdeco-button--primary'
            ];
            
            // Listar botones visibles para debugging
            const allButtons = document.querySelectorAll('button');
            for (let btn of allButtons) {
                if (btn.offsetParent !== null) {
                    debug.visible_buttons++;
                    debug.buttons_found.push({
                        text: btn.textContent.trim().substring(0, 50),
                        aria: (btn.getAttribute('aria-label') || '').substring(0, 50)
                    });
                }
            }
            
            // Buscar botón específico
            for (let selector of buttonSelectors) {
                const buttons = document.querySelectorAll(selector);
                for (let btn of buttons) {
                    if (btn.offsetParent !== null) {
                        const ariaLabel = btn.getAttribute('aria-label') || '';
                        const text = btn.textContent || '';
                        const isSubmit = ariaLabel.toLowerCase().includes('enviar') || 
                                       ariaLabel.toLowerCase().includes('submit') ||
                                       text.toLowerCase().includes('enviar');
                        
                        btn.click();
                        
                        return {
                            found: true,
                            is_submit: isSubmit,
                            button_text: text.trim(),
                            aria_label: ariaLabel,
                            debug: debug
                        };
                    }
                }
            }
            
            return {found: false, debug: debug};
            """
            
            result = self.driver.execute_script(click_script)
            
            if result and result.get('debug'):
                debug = result['debug']
                self.logger.info(f"  → Debug: {debug['total_buttons']} botones totales, {debug['visible_buttons']} visibles")
            
            return result if result else {'found': False}
            
        except Exception as e:
            self.logger.warning(f"  Error buscando botón: {e}")
            return {'found': False}
    
    def _close_modal(self):
        """Cierra el modal sin enviar"""
        try:
            close_script = """
            const closeButtons = document.querySelectorAll('button[aria-label*="Descartar"], button[aria-label*="Dismiss"], button[aria-label*="Close"]');
            for (let btn of closeButtons) {
                if (btn.offsetParent !== null) {
                    btn.click();
                    return true;
                }
            }
            return false;
            """
            closed = self.driver.execute_script(close_script)
            if closed:
                self.logger.info("  ✓ Modal cerrado")
            else:
                self.logger.warning("  ⚠ No se pudo cerrar modal")
        except Exception as e:
            self.logger.warning(f"  Error cerrando modal: {e}")
    
    def detect_captcha_or_block(self) -> bool:
        """
        Detecta si hay CAPTCHA o bloqueo de sesión
        
        Returns:
            True si se detecta CAPTCHA o bloqueo
        """
        try:
            # Detectar CAPTCHA
            captcha_indicators = [
                "div[id*='captcha']",
                "iframe[src*='captcha']",
                "div[class*='captcha']",
                "#px-captcha"
            ]
            
            for selector in captcha_indicators:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element.is_displayed():
                        self.logger.warning("⚠️ CAPTCHA detectado!")
                        return True
                except NoSuchElementException:
                    continue
            
            # Detectar redirect a login (sesión bloqueada)
            current_url = self.driver.current_url
            if '/login' in current_url or '/checkpoint' in current_url:
                self.logger.warning("⚠️ Sesión bloqueada - redirect a login detectado")
                return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Error detectando CAPTCHA: {e}")
            return False
    
    def save_cookies(self):
        """Guarda las cookies de sesión"""
        try:
            cookies = self.driver.get_cookies()
            cookies_file = Path("data/cookies/linkedin_cookies.json")
            cookies_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2)
            
            self.logger.info(f"✓ Cookies guardadas: {len(cookies)} cookies")
            
        except Exception as e:
            self.logger.warning(f"No se pudieron guardar cookies: {e}")
    
    def load_cookies(self):
        """Carga las cookies de sesión guardadas"""
        try:
            cookies_file = Path("data/cookies/linkedin_cookies.json")
            
            if not cookies_file.exists():
                self.logger.info("No hay cookies guardadas")
                return False
            
            with open(cookies_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            # Primero ir a LinkedIn para establecer el dominio
            self.driver.get("https://www.linkedin.com")
            time.sleep(2)
            
            # Agregar cada cookie
            for cookie in cookies:
                try:
                    # Remover campos que pueden causar problemas
                    cookie.pop('sameSite', None)
                    cookie.pop('expiry', None)
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    self.logger.warning(f"No se pudo agregar cookie: {e}")
            
            self.logger.info(f"✓ Cookies cargadas: {len(cookies)} cookies")
            return True
            
        except Exception as e:
            self.logger.warning(f"No se pudieron cargar cookies: {e}")
            return False
    
    def simulate_human_behavior(self):
        """Simula comportamiento humano para evitar detección"""
        try:
            import random
            
            # Scroll gradual aleatorio
            scroll_amount = random.randint(100, 400)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(random.uniform(0.5, 1.5))
            
            # Movimiento de mouse aleatorio (usando JavaScript)
            self.driver.execute_script("""
                const event = new MouseEvent('mousemove', {
                    clientX: Math.random() * window.innerWidth,
                    clientY: Math.random() * window.innerHeight
                });
                document.dispatchEvent(event);
            """)
            
            # Delay variable
            time.sleep(random.uniform(0.3, 0.8))
            
        except Exception as e:
            # No es crítico si falla
            pass
    
    def fill_form_with_javascript(self, job: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """
        Rellena el formulario usando JavaScript puro (más confiable que Selenium)
        
        Args:
            job: Datos del trabajo
            result: Diccionario de resultado
        
        Returns:
            True si se rellenó exitosamente
        """
        try:
            self.logger.info("  → Rellenando formulario con JavaScript...")
            
            personal_info = self.answers.get('informacion_personal', {})
            
            # Primero, guardar HTML para debugging
            try:
                html_content = self.driver.execute_script("return document.body.innerHTML;")
                debug_path = Path(f"data/logs/debug_html_{job['title'][:30]}.html")
                debug_path.parent.mkdir(parents=True, exist_ok=True)
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                self.logger.info(f"  → HTML guardado en: {debug_path}")
            except Exception as e:
                self.logger.warning(f"  No se pudo guardar HTML: {e}")
            
            # Script JavaScript para rellenar el formulario
            fill_script = """
            let filled = {
                email: false,
                phone_country: false,
                phone_number: false,
                fields_found: 0,
                debug: {
                    total_selects: 0,
                    total_inputs: 0,
                    email_selects: 0,
                    phone_selects: 0,
                    phone_inputs: 0
                }
            };
            
            // Contar todos los elementos
            filled.debug.total_selects = document.querySelectorAll('select').length;
            filled.debug.total_inputs = document.querySelectorAll('input[type="text"]').length;
            
            // 1. Rellenar email dropdown
            const emailSelects = document.querySelectorAll('select');
            filled.debug.email_selects = emailSelects.length;
            
            for (let select of emailSelects) {
                const id = select.id || '';
                const label = select.labels?.[0]?.textContent || '';
                const prevLabel = select.previousElementSibling?.textContent || '';
                
                if (id.toLowerCase().includes('email') || 
                    label.toLowerCase().includes('email') || 
                    prevLabel.toLowerCase().includes('email')) {
                    
                    const options = Array.from(select.options);
                    const emailOption = options.find(opt => opt.value && opt.value.includes('@'));
                    if (emailOption) {
                        select.value = emailOption.value;
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                        select.dispatchEvent(new Event('input', { bubbles: true }));
                        filled.email = true;
                        filled.fields_found++;
                    }
                }
            }
            
            // 2. Rellenar phone country code
            const phoneCountrySelects = document.querySelectorAll('select');
            filled.debug.phone_selects = phoneCountrySelects.length;
            
            for (let select of phoneCountrySelects) {
                const id = select.id || '';
                const label = select.labels?.[0]?.textContent || '';
                
                if (id.includes('phoneNumber') && id.includes('country') || 
                    label.toLowerCase().includes('phone') && label.toLowerCase().includes('country')) {
                    
                    const options = Array.from(select.options);
                    const chileOption = options.find(opt => 
                        opt.value && (opt.value.includes('Chile') || opt.value.includes('+56'))
                    );
                    if (chileOption) {
                        select.value = chileOption.value;
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                        select.dispatchEvent(new Event('input', { bubbles: true }));
                        filled.phone_country = true;
                        filled.fields_found++;
                    }
                }
            }
            
            // 3. Rellenar phone number
            const phoneInputs = document.querySelectorAll('input[type="text"]');
            filled.debug.phone_inputs = phoneInputs.length;
            
            for (let input of phoneInputs) {
                const id = input.id || '';
                const label = input.labels?.[0]?.textContent || '';
                const placeholder = input.placeholder || '';
                
                if (id.includes('phoneNumber') || id.includes('phone') ||
                    label.toLowerCase().includes('phone') || 
                    label.toLowerCase().includes('móvil') ||
                    placeholder.toLowerCase().includes('phone')) {
                    
                    input.value = arguments[0];
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    filled.phone_number = true;
                    filled.fields_found++;
                }
            }
            
            return filled;
            """
            
            result_js = self.driver.execute_script(fill_script, personal_info.get('telefono', ''))
            
            # Logging detallado
            if result_js:
                debug_info = result_js.get('debug', {})
                self.logger.info(f"  → Debug: {debug_info['total_selects']} selects, {debug_info['total_inputs']} inputs encontrados")
                
                if result_js.get('fields_found', 0) > 0:
                    self.logger.info(f"  ✓ Campos rellenados con JavaScript: {result_js['fields_found']}")
                    if result_js.get('email'):
                        self.logger.info("    - Email seleccionado")
                    if result_js.get('phone_country'):
                        self.logger.info("    - País de teléfono seleccionado")
                    if result_js.get('phone_number'):
                        self.logger.info("    - Número de teléfono ingresado")
                    return True
                else:
                    self.logger.warning(f"  ⚠ No se encontraron campos para rellenar")
                    self.logger.warning(f"     Elementos en página: {debug_info['total_selects']} selects, {debug_info['total_inputs']} inputs")
                    return False
            else:
                self.logger.warning("  ⚠ JavaScript no retornó resultado")
                return False
                
        except Exception as e:
            self.logger.warning(f"  Error rellenando con JavaScript: {str(e)}")
            import traceback
            self.logger.warning(f"  Traceback: {traceback.format_exc()}")
            return False
    
    def click_next_button_with_javascript(self) -> dict:
        """
        Busca y hace click en el botón Siguiente/Enviar usando JavaScript
        
        Returns:
            Dict con {found: bool, is_submit: bool, button_text: str, debug: dict}
        """
        try:
            click_script = """
            let debug = {
                total_buttons: document.querySelectorAll('button').length,
                visible_buttons: 0,
                buttons_found: []
            };
            
            // Buscar botón de acción
            const buttonSelectors = [
                'button[data-easy-apply-next-button]',
                'button[aria-label*="siguiente"]',
                'button[aria-label*="Next"]',
                'button[aria-label*="Enviar"]',
                'button[aria-label*="Submit"]',
                'button.artdeco-button--primary'
            ];
            
            // Listar todos los botones visibles para debugging
            const allButtons = document.querySelectorAll('button');
            for (let btn of allButtons) {
                if (btn.offsetParent !== null) {
                    debug.visible_buttons++;
                    debug.buttons_found.push({
                        text: btn.textContent.trim().substring(0, 50),
                        aria: (btn.getAttribute('aria-label') || '').substring(0, 50),
                        classes: btn.className.substring(0, 100)
                    });
                }
            }
            
            // Buscar botón específico
            for (let selector of buttonSelectors) {
                const buttons = document.querySelectorAll(selector);
                for (let btn of buttons) {
                    if (btn.offsetParent !== null) {  // Visible
                        const ariaLabel = btn.getAttribute('aria-label') || '';
                        const text = btn.textContent || '';
                        const isSubmit = ariaLabel.toLowerCase().includes('enviar') || 
                                       ariaLabel.toLowerCase().includes('submit') ||
                                       text.toLowerCase().includes('enviar');
                        
                        // Hacer click
                        btn.click();
                        
                        return {
                            found: true,
                            is_submit: isSubmit,
                            button_text: text.trim(),
                            aria_label: ariaLabel,
                            debug: debug
                        };
                    }
                }
            }
            
            return {found: false, debug: debug};
            """
            
            result = self.driver.execute_script(click_script)
            
            # Logging detallado
            if result and result.get('debug'):
                debug = result['debug']
                self.logger.info(f"  → Debug: {debug['total_buttons']} botones totales, {debug['visible_buttons']} visibles")
                
                if not result.get('found') and debug.get('buttons_found'):
                    self.logger.info("  → Botones visibles encontrados:")
                    for btn_info in debug['buttons_found'][:5]:
                        self.logger.info(f"     - '{btn_info['text']}' / aria: '{btn_info['aria']}'")
            
            return result if result else {'found': False}
            
        except Exception as e:
            self.logger.warning(f"  Error haciendo click con JavaScript: {str(e)}")
            import traceback
            self.logger.warning(f"  Traceback: {traceback.format_exc()}")
            return {'found': False}
        """
        Busca elementos en un contexto (puede ser driver, elemento normal, o shadow root)
        
        Args:
            search_context: Contexto donde buscar (driver, elemento, o shadow root)
            by: Tipo de selector (By.CSS_SELECTOR, etc.)
            selector: Selector CSS
        
        Returns:
            Lista de elementos encontrados
        """
        try:
            if search_context is None:
                search_context = self.driver
            
            # Si es un shadow root, usar find_elements directamente
            if hasattr(search_context, 'find_elements'):
                return search_context.find_elements(by, selector)
            else:
                # Fallback al driver
                return self.driver.find_elements(by, selector)
        except Exception as e:
            self.logger.warning(f"  Error buscando elementos: {e}")
            return []
    
    def apply_to_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aplica a un trabajo específico usando IA y sistema de confianza
        
        Args:
            job: Diccionario con datos del trabajo
        
        Returns:
            Diccionario con resultado de la aplicación
        """
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Aplicando a: {job['title']} - {job['company']}")
        self.logger.info(f"{'='*60}")
        
        result = {
            'job_url': job['url'],
            'job_title': job['title'],
            'company': job['company'],
            'success': False,
            'status': 'PENDING',  # Estados: PENDING, APPLIED, MANUAL, NO_DISPONIBLE, ERROR, INSEGURO
            'error': None,
            'questions_encountered': [],
            'questions_answered': [],
            'cv_used': None,
            'confidence_score': None
        }
        
        try:
            # 1. Verificar si trabajo ya fue procesado
            if self.state_manager.is_job_processed(job['url']):
                self.logger.info("✓ Trabajo ya procesado anteriormente, saltando...")
                result['status'] = 'SKIPPED'
                result['error'] = 'Already processed'
                return result
            
            # 2. Verificar CAPTCHA o bloqueo antes de procesar
            if self.detect_captcha_or_block():
                result['error'] = "CAPTCHA o bloqueo de sesión detectado"
                result['status'] = 'ERROR'
                self.logger.error("✗ CAPTCHA o bloqueo detectado - deteniendo ejecución")
                
                # Guardar estado y salir
                self.state_manager.save_job_state(job['url'], 'ERROR', None, result['error'])
                raise Exception("CAPTCHA_DETECTED")  # Esto detendrá el flujo completo
            
            # 3. Ir a la página del trabajo
            self.driver.get(job['url'])
            self.logger.info(f"  Cargando página del trabajo...")
            time.sleep(5)
            
            # Simular comportamiento humano
            self.simulate_human_behavior()
            
            # Scroll para asegurar que el botón esté visible
            self.driver.execute_script("window.scrollTo(0, 300);")
            time.sleep(1)
            
            # 3. Verificar si el trabajo ya no acepta postulaciones (eliminado/cerrado)
            if self._is_job_unavailable():
                result['error'] = "Trabajo ya no acepta postulaciones (eliminado/cerrado)"
                result['status'] = 'NO_DISPONIBLE'
                self.logger.warning("✗ Trabajo cerrado - ya no acepta postulaciones")
                
                # Update state and sheets
                self.state_manager.save_job_state(job['url'], 'NO_DISPONIBLE', None, result['error'])
                if self.sheets_updater:
                    self._update_sheets(job, result)
                
                return result
            
            # 4. Expandir descripción completa (si hay botón "Ver más")
            full_description = self._expand_job_description(job)
            
            # 5. Seleccionar CV con IA
            cv_recommendation = self.cv_selector.select_cv(
                job_title=job['title'],
                job_description=full_description
            )
            
            if cv_recommendation:
                result['cv_used'] = f"{cv_recommendation.cv_type}_{cv_recommendation.language}"
                self.logger.info(f"  ✓ CV seleccionado: {result['cv_used']} (confianza: {cv_recommendation.confidence:.2f})")
                self.logger.info(f"    Razón: {cv_recommendation.reasoning}")
            else:
                result['error'] = "No se pudo seleccionar CV"
                result['status'] = 'ERROR'
                self.state_manager.save_job_state(job['url'], 'ERROR', None, result['error'])
                return result
            
            # 6. Buscar y hacer clic en botón Easy Apply
            # Guardar URL antes del clic para detectar redirects
            url_before_click = self.driver.current_url
            self.logger.info(f"  URL antes del clic: {url_before_click}")
            
            if not self._click_easy_apply_button(result):
                # Error ya registrado en result
                self.state_manager.save_job_state(job['url'], result['status'], result.get('cv_used'), result['error'])
                if self.sheets_updater:
                    self._update_sheets(job, result)
                return result
            
            # 7. Detectar modal con JavaScript (pasar URL inicial para detectar redirects)
            modal_element = self.modal_detector.wait_for_modal(self.driver, timeout=20, initial_url=url_before_click)
            
            if not modal_element:
                result['error'] = "Modal no detectado después de hacer clic en Easy Apply"
                result['status'] = 'MANUAL'
                self.logger.warning("  ⚠ Modal no detectado")
                
                # Save debug HTML
                self._save_debug_html(job, "modal_not_detected")
                
                self.state_manager.save_job_state(job['url'], 'MANUAL', result.get('cv_used'), result['error'])
                if self.sheets_updater:
                    self._update_sheets(job, result)
                
                return result
            
            self.logger.info("  ✓ Modal detectado exitosamente")
            
            # 8. Procesar formulario multi-paso con IA
            aplicacion_exitosa = self._process_application_form_with_ai(
                job, result, modal_element, cv_recommendation, full_description
            )
            
            if aplicacion_exitosa:
                result['success'] = True
                self.logger.success(f"✓ Aplicación enviada exitosamente!")
            else:
                self.logger.warning(f"✗ No se pudo completar la aplicación")
            
            # 9. Guardar estado final
            self.state_manager.save_job_state(
                job['url'], 
                result['status'], 
                result.get('cv_used'), 
                result.get('error')
            )
            
            # 10. Actualizar Google Sheets
            if self.sheets_updater:
                self._update_sheets(job, result)
            
            # 11. Acumular resultado para Telegram
            if self.telegram_notifier:
                self.telegram_notifier.accumulate_result(job, result)
            
        except Exception as e:
            result['error'] = str(e)
            result['status'] = 'ERROR'
            self.logger.error(f"Error aplicando: {str(e)}")
            
            # Save error state
            self.state_manager.save_job_state(job['url'], 'ERROR', result.get('cv_used'), str(e))
            if self.sheets_updater:
                self._update_sheets(job, result)
        
        return result
    
    def process_application_form(self, job: Dict[str, Any], result: Dict[str, Any], modal_element=None) -> bool:
        """
        Procesa el formulario de aplicación multi-paso
        
        Args:
            job: Datos del trabajo
            result: Diccionario de resultado (se modifica)
            modal_element: Elemento del modal (para buscar dentro de él)
        
        Returns:
            True si se completó exitosamente, False si no
        """
        max_steps = 10
        current_step = 0
        
        # Trackear preguntas ya vistas para evitar duplicados
        seen_questions = set()
        questions_without_answer = []
        
        # Detectar si estamos en loop (mismo botón varias veces)
        button_history = []
        
        # Esperar un poco más para que el modal cargue completamente
        time.sleep(3)
        
        # Si no tenemos referencia al modal O es el flag "javascript", usar JavaScript puro
        use_javascript = (modal_element == "javascript" or modal_element is None)
        search_context = None if use_javascript else modal_element
        
        if use_javascript:
            self.logger.info("  → Usando JavaScript para interactuar con el formulario")
        
        while current_step < max_steps:
            current_step += 1
            self.logger.info(f"  Paso {current_step}...")
            
            time.sleep(2)
            
            # Rellenar formulario
            if use_javascript:
                # Usar JavaScript puro
                filled = self.fill_form_with_javascript(job, result)
            else:
                # Usar Selenium tradicional
                new_questions = self.fill_current_form_step(job, result, seen_questions, search_context)
                questions_without_answer.extend(new_questions)
            
            # Si hay más de 3 preguntas sin respuesta, abortar
            if len(questions_without_answer) > 3:
                self.logger.warning(f"  ✗ Demasiadas preguntas sin respuesta ({len(questions_without_answer)}). Marcando como MANUAL.")
                result['error'] = f"Requiere {len(questions_without_answer)} respuestas manuales"
                result['status'] = 'MANUAL'
                return False
            
            time.sleep(1)
            
            # Buscar y hacer click en botón
            if use_javascript:
                # Usar JavaScript para buscar y hacer click
                button_result = self.click_next_button_with_javascript()
                
                if button_result.get('found'):
                    button_text = button_result.get('button_text', '')
                    is_submit = button_result.get('is_submit', False)
                    
                    self.logger.info(f"  ✓ Click en botón: '{button_text}' (JavaScript)")
                    
                    time.sleep(2)
                    
                    if is_submit:
                        self.logger.success("  ✓ Aplicación enviada!")
                        result['status'] = 'APPLIED'
                        result['success'] = True
                        return True
                else:
                    self.logger.warning("  ⚠ No se encontró botón con JavaScript")
                    result['error'] = f"No se encontró botón en paso {current_step}"
                    result['status'] = 'MANUAL'
                    return False
            else:
                # Usar Selenium tradicional (código existente)
                next_button = None
                button_selectors = [
                    # Botones de envío (prioridad alta)
                    "button[aria-label*='Enviar']",
                    "button[aria-label*='Submit']",
                    "button[aria-label*='Send application']",
                    "button[aria-label*='Enviar solicitud']",
                    # Botones de navegación
                    "button[aria-label*='Continuar']",
                    "button[aria-label*='Continue']",
                    "button[aria-label*='siguiente']",
                    "button[aria-label*='Next']",
                    "button[aria-label*='Siguiente']",
                    "button[data-easy-apply-next-button]",
                    "button[aria-label*='Review']",
                    "button[aria-label*='Revisar']",
                    # Selectores genéricos (última opción)
                    "button.artdeco-button--primary",
                    "button[type='button'].artdeco-button"
                ]
                
                for selector in button_selectors:
                    try:
                        buttons = self.find_elements_in_context(search_context, By.CSS_SELECTOR, selector)
                        for btn in buttons:
                            if btn.is_displayed() and btn.is_enabled():
                                # Verificar que no sea el botón de cerrar
                                aria_label = btn.get_attribute('aria-label') or ''
                                if 'descartar' in aria_label.lower() or 'dismiss' in aria_label.lower() or 'close' in aria_label.lower():
                                    continue
                                next_button = btn
                                self.logger.info(f"  ✓ Botón encontrado con selector: {selector}")
                                break
                        if next_button:
                            break
                    except NoSuchElementException:
                        continue
            
            if not next_button:
                self.logger.warning("  ⚠ No se encontró botón de acción")
                
                # Intentar buscar cualquier botón visible en el modal
                try:
                    all_buttons = self.find_elements_in_context(search_context, By.CSS_SELECTOR, "button")
                    visible_buttons = [btn for btn in all_buttons if btn.is_displayed() and btn.is_enabled()]
                    
                    if visible_buttons:
                        self.logger.info(f"  ℹ Encontrados {len(visible_buttons)} botones visibles EN EL MODAL")
                        for btn in visible_buttons[:5]:  # Mostrar primeros 5
                            aria = btn.get_attribute('aria-label') or ''
                            text = btn.text or ''
                            self.logger.info(f"    - Botón: '{text}' / aria-label: '{aria}'")
                    else:
                        self.logger.warning("  ⚠ No se encontraron botones visibles en el modal")
                except Exception as e:
                    self.logger.warning(f"  Error listando botones: {e}")
                
                screenshot_path = Path(f"data/logs/debug_no_next_button_{current_step}.png")
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                self.driver.save_screenshot(str(screenshot_path))
                self.logger.info(f"  Screenshot guardado: {screenshot_path}")
                
                result['error'] = f"No se encontró botón en paso {current_step}"
                result['status'] = 'MANUAL'
                return False
            
            button_aria_label = next_button.get_attribute('aria-label') or ''
            button_text = next_button.text or button_aria_label
            
            # IMPORTANTE: Detectar botón "Enviar" ANTES de hacer click
            button_context = f"{button_text} {button_aria_label}".lower()
            is_submit_button = any(word in button_context for word in ['enviar', 'submit', 'send application', 'enviar solicitud'])
            
            # Detectar loop infinito
            button_history.append(button_aria_label)
            if len(button_history) > 3:
                # Si los últimos 3 botones son iguales, estamos en loop
                if button_history[-1] == button_history[-2] == button_history[-3]:
                    self.logger.warning(f"  ✗ Detectado loop infinito (mismo botón '{button_text}' 3+ veces)")
                    result['error'] = "Loop infinito detectado - formulario bloqueado"
                    result['status'] = 'MANUAL'
                    return False
            
            self.logger.info(f"  Botón encontrado: '{button_text}' (aria-label: '{button_aria_label}')")
            
            # Click en el botón
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                time.sleep(0.5)
                next_button.click()
                self.logger.info(f"  ✓ Click en '{button_text}'")
            except Exception as e:
                try:
                    self.driver.execute_script("arguments[0].click();", next_button)
                    self.logger.info(f"  ✓ Click en '{button_text}' (JavaScript)")
                except Exception as e2:
                    self.logger.error(f"  ✗ Error en click: {e2}")
                    result['error'] = f"No se pudo hacer click en botón: {e2}"
                    result['status'] = 'ERROR'
                    return False
            
            time.sleep(2)
            
            # Si era botón "Enviar", aplicación completa
            if is_submit_button:
                # Esperar confirmación
                time.sleep(3)
                self.logger.success("  ✓ Aplicación enviada!")
                result['status'] = 'APPLIED'
                result['success'] = True
                return True
        
        self.logger.warning("  Se alcanzó el límite de pasos")
        result['status'] = 'MANUAL'
        result['error'] = f"Se alcanzó límite de {max_steps} pasos sin completar"
        return False
    
    def fill_current_form_step(self, job: Dict[str, Any], result: Dict[str, Any], seen_questions: set, search_context=None) -> list:
        """
        Rellena el paso actual del formulario
        
        Args:
            job: Datos del trabajo
            result: Diccionario de resultado
            seen_questions: Set de preguntas ya vistas (para evitar duplicados)
            search_context: Elemento donde buscar (modal o driver completo)
        
        Returns:
            Lista de preguntas nuevas sin respuesta
        """
        new_questions = []
        
        # Si no hay contexto, usar driver completo (fallback)
        if search_context is None:
            search_context = self.driver
        
        try:
            self.logger.info("  → Rellenando formulario...")
            
            # 1. Upload CV si es necesario
            cv_uploaded = self.handle_cv_upload(job, result, search_context)
            
            # 2. Buscar y rellenar campos de texto (DENTRO DEL MODAL)
            # Usar selectores más específicos para campos del formulario
            text_field_selectors = [
                "input[type='text'][data-test-single-line-text-form-component]",  # Campos específicos del form
                "input[type='email']",
                "input[type='tel']",
                "input[type='text']"  # Genérico como fallback
            ]
            
            text_fields = []
            for selector in text_field_selectors:
                try:
                    fields = self.find_elements_in_context(search_context, By.CSS_SELECTOR, selector)
                    text_fields.extend(fields)
                except:
                    continue
            
            if text_fields:
                self.logger.info(f"  → Encontrados {len(text_fields)} campos de texto EN EL MODAL")
                for field in text_fields:
                    self.fill_text_field(field, result)
            
            # 3. Buscar y rellenar textareas (DENTRO DEL MODAL)
            textareas = self.find_elements_in_context(search_context, By.TAG_NAME, "textarea")
            if textareas:
                self.logger.info(f"  → Encontrados {len(textareas)} textareas EN EL MODAL")
                for textarea in textareas:
                    self.fill_textarea(textarea, result)
            
            # 4. Buscar y responder preguntas de radio/checkbox (DENTRO DEL MODAL)
            self.handle_radio_questions(result, seen_questions, new_questions, search_context)
            
            # 5. Buscar y responder dropdowns (DENTRO DEL MODAL)
            # Filtrar dropdowns del formulario específicamente
            self.handle_dropdown_questions(result, seen_questions, new_questions, search_context)
            
            if not text_fields and not textareas and not new_questions:
                self.logger.info("  → No se encontraron campos para rellenar en este paso")
            
            return new_questions
            
        except Exception as e:
            self.logger.warning(f"  Error rellenando formulario: {str(e)}")
            return new_questions
    
    def handle_cv_upload(self, job: Dict[str, Any], result: Dict[str, Any], search_context=None) -> bool:
        """Maneja la subida de CV"""
        if search_context is None:
            search_context = self.driver
            
        try:
            # Buscar input de archivo
            file_inputs = self.find_elements_in_context(search_context, By.CSS_SELECTOR, "input[type='file']")
            
            if not file_inputs:
                return True  # No hay upload, está bien
            
            # Seleccionar CV apropiado
            cv_type = select_cv_by_keywords(
                job.get('title', ''),
                job.get('description', ''),
                self.config
            )
            
            cv_path = self.cv_paths.get(cv_type)
            
            if not cv_path or not Path(cv_path).exists():
                self.logger.warning(f"  CV no encontrado: {cv_path}")
                return False
            
            # Subir CV
            file_inputs[0].send_keys(str(Path(cv_path).absolute()))
            result['cv_used'] = cv_type
            self.logger.info(f"  ✓ CV subido: {cv_type}")
            time.sleep(2)
            
            return True
            
        except Exception as e:
            self.logger.warning(f"  Error subiendo CV: {str(e)}")
            return False
    
    def fill_text_field(self, field, result: Dict[str, Any]):
        """Rellena un campo de texto basándose en su label/placeholder"""
        try:
            # Obtener información del campo
            field_id = field.get_attribute('id') or ''
            field_name = field.get_attribute('name') or ''
            placeholder = field.get_attribute('placeholder') or ''
            aria_label = field.get_attribute('aria-label') or ''
            
            # Buscar label asociado
            label_text = ""
            try:
                if field_id:
                    label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{field_id}']")
                    label_text = label.text.lower()
            except NoSuchElementException:
                pass
            
            # Combinar todos los indicadores
            field_context = f"{label_text} {placeholder} {aria_label} {field_name}".lower()
            
            # Si ya tiene valor, no sobrescribir
            if field.get_attribute('value'):
                return
            
            # Determinar qué llenar
            personal_info = self.answers.get('informacion_personal', {})
            
            if any(word in field_context for word in ['email', 'correo', 'e-mail']):
                field.send_keys(personal_info.get('email', ''))
                self.logger.info(f"  ✓ Email ingresado")
            
            elif any(word in field_context for word in ['phone', 'teléfono', 'telefono', 'celular']):
                field.send_keys(personal_info.get('telefono', ''))
                self.logger.info(f"  ✓ Teléfono ingresado")
            
            elif any(word in field_context for word in ['linkedin', 'linkedin url']):
                field.send_keys(personal_info.get('linkedin_url', ''))
                self.logger.info(f"  ✓ LinkedIn URL ingresado")
            
            elif any(word in field_context for word in ['city', 'ciudad', 'location', 'ubicación']):
                field.send_keys(personal_info.get('ciudad', ''))
                self.logger.info(f"  ✓ Ciudad ingresada")
            
        except Exception as e:
            pass  # Silenciosamente continuar si falla un campo
    
    def fill_textarea(self, textarea, result: Dict[str, Any]):
        """Rellena un textarea (probablemente carta de presentación)"""
        try:
            # Si ya tiene contenido, no sobrescribir
            if textarea.get_attribute('value'):
                return
            
            aria_label = textarea.get_attribute('aria-label') or ''
            placeholder = textarea.get_attribute('placeholder') or ''
            
            context = f"{aria_label} {placeholder}".lower()
            
            respuestas_abiertas = self.answers.get('respuestas_abiertas_template', {})
            
            if any(word in context for word in ['cover letter', 'carta', 'presentación', 'motivación']):
                cover_letter = respuestas_abiertas.get('por_que_empresa', '')
                textarea.send_keys(cover_letter)
                self.logger.info(f"  ✓ Carta de presentación ingresada")
            
        except Exception as e:
            pass
    
    def handle_radio_questions(self, result: Dict[str, Any], seen_questions: set, new_questions: list, search_context=None):
        """Maneja preguntas de tipo radio button"""
        if search_context is None:
            search_context = self.driver
            
        try:
            radio_groups = self.find_elements_in_context(search_context, By.CSS_SELECTOR, "fieldset, div[role='radiogroup']")
            
            for group in radio_groups:
                try:
                    legend = group.find_element(By.TAG_NAME, "legend")
                    question_text = legend.text.lower().strip()
                    
                    # Si ya vimos esta pregunta, skip
                    if question_text in seen_questions:
                        continue
                    
                    answer = self.find_answer_for_question(question_text)
                    
                    if answer:
                        radios = group.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                        for radio in radios:
                            label = radio.find_element(By.XPATH, "./following-sibling::label")
                            if answer.lower() in label.text.lower():
                                radio.click()
                                self.logger.info(f"  ✓ Respondido: {question_text[:50]}... → {answer}")
                                seen_questions.add(question_text)
                                break
                    else:
                        if question_text and question_text not in seen_questions:
                            new_questions.append(question_text)
                            seen_questions.add(question_text)
                            result['questions_encountered'].append(question_text)
                            self.logger.warning(f"  ? Pregunta sin respuesta: {question_text[:50]}...")
                        
                except Exception:
                    continue
                    
        except Exception as e:
            pass
    
    def handle_dropdown_questions(self, result: Dict[str, Any], seen_questions: set, new_questions: list, search_context=None):
        """Maneja preguntas de tipo dropdown/select"""
        if search_context is None:
            search_context = self.driver
            
        try:
            # Buscar solo dropdowns dentro del formulario (con data-test-form-element)
            selects = self.find_elements_in_context(search_context, By.CSS_SELECTOR, "select[data-test-text-entity-list-form-select], select")
            
            # Filtrar dropdowns que NO sean de idioma de LinkedIn
            form_selects = []
            for select in selects:
                select_id = select.get_attribute('id') or ''
                # Ignorar dropdown de idioma de LinkedIn
                if 'language' in select_id.lower() or 'locale' in select_id.lower():
                    continue
                # Solo incluir si tiene data-test o está dentro de un form
                if select.get_attribute('data-test-text-entity-list-form-select') or select.find_element(By.XPATH, "./ancestor::form"):
                    form_selects.append(select)
            
            if not form_selects:
                # Fallback: usar todos los selects encontrados excepto idioma
                form_selects = [s for s in selects if 'language' not in (s.get_attribute('id') or '').lower()]
            
            for select in form_selects:
                try:
                    select_id = select.get_attribute('id') or ''
                    aria_label = select.get_attribute('aria-label') or ''
                    
                    # Buscar label
                    label_text = ""
                    if select_id:
                        try:
                            label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{select_id}']")
                            label_text = label.text.lower()
                        except:
                            pass
                    
                    question_text = f"{label_text} {aria_label}".lower().strip()
                    
                    # Si ya vimos esta pregunta, skip
                    if question_text in seen_questions:
                        continue
                    
                    # Verificar si ya tiene un valor válido seleccionado
                    current_value = select.get_attribute('value')
                    if current_value and current_value not in ["Selecciona una opción", "Select an option", ""]:
                        self.logger.info(f"  ✓ Dropdown ya tiene valor: {current_value[:50]}")
                        seen_questions.add(question_text)
                        continue
                    
                    # Casos especiales: Email y teléfono de LinkedIn
                    from selenium.webdriver.support.ui import Select
                    select_obj = Select(select)
                    
                    if 'email' in question_text or 'correo' in question_text:
                        for option in select_obj.options[1:]:
                            if '@' in option.text:
                                select_obj.select_by_visible_text(option.text)
                                self.logger.info(f"  ✓ Email seleccionado: {option.text}")
                                seen_questions.add(question_text)
                                break
                        continue
                    
                    if 'phone' in question_text or 'teléfono' in question_text or 'telefono' in question_text:
                        for option in select_obj.options[1:]:
                            if any(char.isdigit() for char in option.text):
                                select_obj.select_by_visible_text(option.text)
                                self.logger.info(f"  ✓ Teléfono seleccionado: {option.text}")
                                seen_questions.add(question_text)
                                break
                        continue
                    
                    # Para otras preguntas, buscar respuesta configurada
                    answer = self.find_answer_for_question(question_text)
                    
                    if answer:
                        for option in select_obj.options:
                            if answer.lower() in option.text.lower():
                                select_obj.select_by_visible_text(option.text)
                                self.logger.info(f"  ✓ Seleccionado: {question_text[:50]}... → {option.text}")
                                seen_questions.add(question_text)
                                break
                    else:
                        # Pregunta sin respuesta - agregar solo si no está duplicada
                        if question_text and question_text not in seen_questions:
                            new_questions.append(question_text)
                            seen_questions.add(question_text)
                            result['questions_encountered'].append(question_text)
                            self.logger.warning(f"  ? Dropdown sin respuesta: {question_text[:50]}...")
                        
                except Exception as e:
                    self.logger.warning(f"  Error en dropdown: {str(e)}")
                    continue
                    
        except Exception as e:
            pass
    
    def find_answer_for_question(self, question_text: str) -> Optional[str]:
        """
        Busca una respuesta configurada para una pregunta
        
        Args:
            question_text: Texto de la pregunta
        
        Returns:
            Respuesta si se encuentra, None si no
        """
        import re
        
        preguntas_config = self.answers.get('preguntas_configuradas', {})
        
        for pregunta_key, pregunta_data in preguntas_config.items():
            # Obtener patrón de la pregunta
            if isinstance(pregunta_data, dict):
                patron = pregunta_data.get('pregunta_patron', '')
                patrones = pregunta_data.get('patrones', [patron]) if patron else pregunta_data.get('patrones', [])
            else:
                continue
            
            # Verificar si algún patrón coincide
            for patron in patrones:
                if re.search(patron, question_text, re.IGNORECASE):
                    # Obtener respuesta
                    if 'respuesta' in pregunta_data:
                        return pregunta_data['respuesta']
                    elif 'respuestas' in pregunta_data:
                        respuestas = pregunta_data['respuestas']
                        if isinstance(respuestas, dict):
                            return respuestas.get('corta') or respuestas.get('default') or list(respuestas.values())[0]
                        return str(respuestas)
                    break
        
        return None


def main():
    """Función principal de prueba"""
    from linkedin_scraper import LinkedInScraper
    
    print("🤖 LinkedIn Job Applier - Con IA y Sistema de Confianza")
    print("=" * 60)
    
    config = Config()
    logger = Logger()
    
    # Cargar credenciales
    credentials = config.get_linkedin_credentials()
    if not credentials:
        logger.error("No se pudieron cargar credenciales")
        return
    
    # Cargar trabajos nuevos
    jobs_file = Path("data/logs/new_jobs_to_apply.json")
    if not jobs_file.exists():
        logger.info("No hay trabajos para aplicar (new_jobs_to_apply.json no existe)")
        return
    
    with open(jobs_file, 'r', encoding='utf-8') as f:
        all_jobs = json.load(f)
    
    # Filtrar solo trabajos nuevos con Easy Apply
    pending_jobs = [job for job in all_jobs if job.get('has_easy_apply')]
    
    logger.info(f"Trabajos pendientes de aplicar: {len(pending_jobs)}")
    
    if len(pending_jobs) == 0:
        logger.info("No hay trabajos nuevos con Easy Apply")
        return
    
    # Crear scraper (para reutilizar driver y login)
    scraper = LinkedInScraper(config, logger, headless=False)
    scraper.setup_driver()
    
    # Crear applier con nuevos componentes
    applier = LinkedInApplier(scraper.driver, config, logger)
    
    # Intentar cargar cookies guardadas
    cookies_loaded = applier.load_cookies()
    
    if cookies_loaded:
        logger.info("✓ Cookies cargadas, verificando sesión...")
        # Ir a LinkedIn para verificar si la sesión es válida
        scraper.driver.get("https://www.linkedin.com/feed/")
        time.sleep(3)
        
        # Verificar si estamos logueados
        try:
            scraper.driver.find_element(By.CSS_SELECTOR, "nav.global-nav")
            logger.info("✓ Sesión válida con cookies")
        except NoSuchElementException:
            logger.info("Cookies expiradas, haciendo login...")
            if not scraper.login(credentials['username'], credentials['password']):
                logger.error("Login fallido")
                return
            applier.save_cookies()
    else:
        # Login normal
        if not scraper.login(credentials['username'], credentials['password']):
            logger.error("Login fallido")
            return
        applier.save_cookies()
    
    # Aplicar a trabajos
    results = []
    captcha_detected = False
    
    for i, job in enumerate(pending_jobs):
        logger.info(f"\n--- Trabajo {i+1}/{len(pending_jobs)} ---")
        
        try:
            result = applier.apply_to_job(job)
            results.append(result)
        except Exception as e:
            if "CAPTCHA_DETECTED" in str(e):
                logger.error("⚠️ CAPTCHA detectado - deteniendo ejecución")
                captcha_detected = True
                
                # Marcar trabajos restantes como pendientes
                for remaining_job in pending_jobs[i:]:
                    applier.state_manager.save_job_state(
                        remaining_job['url'], 
                        'PENDING', 
                        None, 
                        'Ejecución detenida por CAPTCHA'
                    )
                break
            else:
                logger.error(f"Error inesperado: {e}")
                results.append({
                    'job_url': job['url'],
                    'job_title': job['title'],
                    'company': job['company'],
                    'success': False,
                    'status': 'ERROR',
                    'error': str(e)
                })
        
        # Delay aleatorio entre aplicaciones (anti-bot)
        if i < len(pending_jobs) - 1:  # No esperar después del último
            import random
            delay = random.uniform(8, 15)
            logger.info(f"  Esperando {delay:.1f}s antes de siguiente aplicación...")
            time.sleep(delay)
    
    # Guardar cookies al final
    if not captcha_detected:
        applier.save_cookies()
    
    # Enviar resumen consolidado por Telegram
    if applier.telegram_notifier and not captcha_detected:
        try:
            logger.info("\n" + "="*60)
            logger.info("Enviando resumen por Telegram...")
            applier.telegram_notifier.send_summary()
            logger.info("✓ Resumen enviado por Telegram")
        except Exception as e:
            logger.warning(f"No se pudo enviar resumen por Telegram: {e}")
    
    # Mostrar resumen en consola
    logger.info(f"\n{'='*60}")
    logger.info("RESUMEN DE APLICACIONES")
    logger.info(f"{'='*60}")
    
    successful = sum(1 for r in results if r.get('status') == 'APPLIED')
    uncertain = sum(1 for r in results if r.get('status') == 'INSEGURO')
    manual = sum(1 for r in results if r.get('status') == 'MANUAL')
    unavailable = sum(1 for r in results if r.get('status') == 'NO_DISPONIBLE')
    errors = sum(1 for r in results if r.get('status') == 'ERROR')
    
    logger.info(f"Total procesados: {len(results)}")
    logger.info(f"✅ Exitosos: {successful}")
    logger.info(f"⚠️  Inseguros: {uncertain}")
    logger.info(f"👤 Requieren revisión manual: {manual}")
    logger.info(f"❌ No disponibles: {unavailable}")
    logger.info(f"🔴 Errores: {errors}")
    
    # Guardar resultados
    results_file = Path("data/logs/application_results.json")
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.success(f"Resultados guardados en: {results_file}")
    
    # Limpiar estado antiguo
    applier.state_manager.cleanup_old_entries()
    
    scraper.close()


if __name__ == "__main__":
    main()